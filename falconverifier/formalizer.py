from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from . import arabic, arabic_graph, arabic_logic
from .llm import ChatModel, extract_json
from .memory import Memory
from .schemas import Formalization, FormalStep, ReasoningStep, Verdict, VerificationReport
from .student import yes_no_polarity

log = logging.getLogger(__name__)

SYSTEM_PROMPT = r"""You are an expert in Lean 4 and Mathlib. You translate natural-language
reasoning steps into Lean 4 propositions so that a proof assistant can check them.

Output a single JSON object and nothing else:
{
  "problem_prop": "<Lean Prop stating that the FINAL ANSWER is correct, derived from the
                   PROBLEM data, or null if the problem cannot be expressed formally>",
  "steps": [
    {"index": 1, "kind": "arith|algebra|logic|skip", "lean_prop": "<Lean Prop or null>",
     "note": "<short justification>"}
  ]
}

Translation rules (follow strictly):
- Each `lean_prop` is a closed Lean 4 Prop: NO `theorem`, NO `:=`, NO proof, NO free variables.
- Give every numeric literal a type: `(17:ℕ)`, `(3:ℤ)`, `(2.5:ℝ)`. Use ℕ only when there is no
  subtraction or division. Use ℚ or ℝ for fractions, percentages, decimals, division.
- Parenthesize numerators and denominators: an average "(64+75+80+81)/4 = 75" must be
  `((64:ℚ) + 75 + 80 + 81) / 4 = 75`, never `(64:ℚ) + 75 + 80 + 81 / 4 = 75`.
- A step like "solve 2x+3=11, so x=4" becomes `(2:ℝ) * 4 + 3 = 11` (substitute the claimed
  value). A step "x=4 is the ONLY solution" becomes `∀ x : ℝ, 2 * x + 3 = 11 → x = 4`.
- A step that claims an inequality: `(45:ℕ) < 60`.
- Multi-claim steps: join with ∧, e.g. `(17:ℕ) * 20 = 340 ∧ (17:ℕ) * 3 = 51`.
- Categorical / syllogistic logic ("all A are B", "some B are C" ⇒ ...): quantify over a
  small finite universe using Bool predicates so that Lean can decide it by enumeration:
  `∀ (A B C : Fin 3 → Bool), (∀ x, A x → B x) → (∃ x, B x ∧ C x) → ∃ x, A x ∧ C x`.
  Encode: "all A are B" ↦ `∀ x, A x → B x`; "some A are B" ↦ `∃ x, A x ∧ B x`;
  "no A are B" ↦ `∀ x, A x → ¬ B x`; "some A are not B" ↦ `∃ x, A x ∧ ¬ B x`.
- Propositional reasoning ("if P then Q; not Q; therefore not P"):
  `∀ (P Q : Prop), (P → Q) → ¬Q → ¬P`.
- Ordering / comparison puzzles with named entities: use variables over ℕ or ℤ:
  `∀ (a b c : ℤ), a > b → b > c → a > c`.
- A relation BETWEEN people (friends, handshakes, knows, played against) is a BINARY
  relation `f : Fin n → Fin n → Bool`, never a per-person Bool. Symmetric-relation counting
  puzzles ("n people, each has exactly k friends among them — must someone be lying?") use
  the library predicate `FalconVerifier.Regular f k` (symmetric, irreflexive, every vertex
  has degree k): "possible" ↦ `∃ f : Fin n → Fin n → Bool, FalconVerifier.Regular f k`;
  "someone must lie" ↦ `∀ f : Fin n → Fin n → Bool, ¬ FalconVerifier.Regular f k`.
  Never write `∀ x, ∑ y, …` or hand-rolled degree sums over the relation.
- Steps that only restate the problem, set notation, or contain no checkable claim get
  `"kind": "skip", "lean_prop": null`.
- Translate what the step ASSERTS, with its polarity. If a step says an inference does NOT
  follow / cannot be concluded / is not guaranteed, the claim is the NEGATION:
  `¬ (∀ (A B C : Fin 3 → Bool), ...)`. If a step only says something is "possible" or
  "not specified", skip it. Never turn a negative statement into a positive claim.
- `problem_prop` must be computed from the problem statement itself (not from the student's
  intermediate numbers) and assert the student's FINAL ANSWER, e.g. if the problem is
  "3 boxes of 12 apples, 7 given away, how many left?" and the final answer is 31,
  write `(3:ℕ) * 12 - 7 = 31`. For yes/no logic questions use the full logical statement if the
  answer is Yes, or its negation `¬ (...)` if the answer is No.
- Prefer simple expressions the tactics norm_num / decide / omega / linarith can close.
- Mathlib names: `Nat.Prime p`, `Odd n`, `Even n`, `a ∣ b` (divides), `n % 3 = 0`; never bare
  `prime`, `odd`, `mod`. A single counterexample question ("does 3 ∣ n imply 6 ∣ n?") is a
  closed ∀ over ℕ, negated `¬ (∀ n : ℕ, …)` when the answer is No.
- Never invent facts that are not in the problem or the steps.
- The problem and steps may be in Arabic (Modern Standard Arabic, possibly with Eastern
  Arabic digits ٠١٢٣٤٥٦٧٨٩). Translate the mathematics exactly as written; word order
  (VSO/SVO) does not change the claim. «نعم» = Yes, «لا» = No, «كل» = all, «بعض» = some,
  «ليس»/«لا» = not, «إذا ... فإن» = if ... then, «يقبل القسمة على» = is divisible by.
  «لا أحد من A» = no A are ...; «بعض A» is ∃, NEVER ∀. Lean identifiers must be ASCII: a
  named individual («خالد») becomes a bound variable `∀ (k : Fin 3), ...` or the literal
  `(0 : Fin 3)`, never an Arabic identifier and never `Fin.of_nat`/`Sultan`-style constants.
- A premise that is simply asserted ("all doctors are educated") is NOT a universally
  quantified schema over all predicates — that would be false. Encode a bare premise as
  `"kind": "skip"`; only encode the INFERENCE (premises → conclusion) as a closed ∀-statement.
"""

FEWSHOT_USER = """PROBLEM:
A shop sells pencils at 3 for $2. How much do 12 pencils cost?

STUDENT STEPS:
Step 1: 12 pencils is 12 / 3 = 4 groups of 3.
Step 2: Each group costs $2, so the total is 4 × 2 = $8.
FINAL ANSWER: 8"""

FEWSHOT_ASSISTANT = """{
  "problem_prop": "(12:ℚ) / 3 * 2 = 8",
  "steps": [
    {"index": 1, "kind": "arith", "lean_prop": "(12:ℚ) / 3 = 4", "note": "groups of three"},
    {"index": 2, "kind": "arith", "lean_prop": "(4:ℚ) * 2 = 8", "note": "total cost"}
  ]
}"""

FEWSHOT_USER2 = """PROBLEM:
All squares are rectangles. Some rectangles are not squares. Does it follow that some squares are not rectangles? Answer Yes or No.

STUDENT STEPS:
Step 1: All squares are rectangles means every square is a rectangle.
Step 2: Some rectangles are not squares means there is a rectangle that is not a square.
Step 3: From these, some squares are not rectangles.
FINAL ANSWER: Yes"""

FEWSHOT_ASSISTANT2 = """{
  "problem_prop": "∀ (S R : Fin 3 → Bool), (∀ x, S x → R x) → (∃ x, R x ∧ ¬ S x) → ∃ x, S x ∧ ¬ R x",
  "steps": [
    {"index": 1, "kind": "skip", "lean_prop": null, "note": "restates premise"},
    {"index": 2, "kind": "skip", "lean_prop": null, "note": "restates premise"},
    {"index": 3, "kind": "logic", "lean_prop": "∀ (S R : Fin 3 → Bool), (∀ x, S x → R x) → (∃ x, R x ∧ ¬ S x) → ∃ x, S x ∧ ¬ R x", "note": "the inference"}
  ]
}"""

AUDIT_PROMPT = """You are auditing a formalization. The Lean 4 kernel has ALREADY PROVED this
proposition FALSE. Your only job is to decide whether the proposition is a FAITHFUL
translation of what the student's step says: same claim, same polarity (a step that denies
a conclusion must be translated as a negation), same numbers, same operations.

Do NOT judge whether the step is mathematically correct — a faithful translation of a wrong
step is still faithful (answer true). Answer false ONLY if the proposition says something
different from the step (wrong numbers, wrong operation, flipped negation, extra or missing
premises).

If the step is the student's FINAL ANSWER to a yes/no question, the proposition must say
"the answer is correct": for "Yes" it is the inference itself (premises → conclusion), for
"No" it is the NEGATION `¬ (…)` of that inference. A proposition of that shape whose premises
and conclusion match the question IS faithful, even though it is more general than the
question's named individuals (finite domains and bound variables stand for them).

Problem: {problem}
Step text: {step}
Lean proposition: {prop}

Answer with a JSON object: {{"faithful": true|false, "reason": "<one sentence>"}}"""

YESNO_AUDIT_PROMPT = """You are auditing the formalization of a yes/no logic question. Polarity has
already been handled mechanically (the student answered {answer!r}; the checked proposition
is the inference itself for Yes, its negation for No). Your ONLY job: does the inference
below encode exactly the question — same premises, same conclusion, quantifiers preserved
("all" → ∀, "some" → ∃, "no A are B" → ∀ x, A x → ¬ B x), named individuals allowed to be bound
variables or elements of a finite type, transitivity/ordering puzzles allowed to use integers?

Do NOT judge whether the inference is valid, and do NOT complain that it is "more general" than
the question, that it uses ∀/Fin/ℤ/abstract P Q instead of the concrete nouns ("it rained"
↦ P is FINE — propositional schemas are the intended encoding), or that the student's answer is
short. Answer false ONLY if a premise stated in the question is completely absent, an extra
premise was invented, the conclusion is about a different relation/direction than the
question asks, or the formula is degenerate (a premise repeated as the conclusion). When in
doubt answer true — the Lean kernel, not you, decides validity.

Question (may be Arabic): {problem}
Inference as formalized: {prop}

Answer with a JSON object: {{"faithful": true|false, "reason": "<one sentence>"}}"""

SIGNATURE_PROMPT = """Extract the logical SIGNATURE of the question below (it may be Arabic). Do not
answer the question. Return a JSON object with exactly these keys:

- "binary_relations": relations that hold between TWO NAMED OR COUNTED PEOPLE/OBJECTS of the
  same group, e.g. "Omar is taller than Yusuf", "each student is a friend of 3 others",
  "every guest shook hands with". Give each as {{"relation": "...", "between": "<who and
  whom>"}}. Statements that one CLASS is contained in / excluded from another ("all birds are
  animals", "no bird is a mammal", "some doctors are rich") are class statements, NOT binary
  relations — leave the list EMPTY for pure syllogisms. Whole-sentence facts ("it rained") are
  not relations either.
- "symmetric": true if at least one listed binary relation is mutual by meaning
  (friendship, handshake, acquaintance, played against), else false.
- "counts": integers that the claim structurally depends on — group sizes ("5 students") and
  per-individual counts ("exactly 3 of the others"). Exclude numbers used only as labels.

Question: {problem}"""

REPAIR_PROMPT = """Some of your Lean propositions failed to type-check. Fix them and return the
complete JSON object again (same schema, all steps). Lean errors:

{errors}

Common fixes: add numeric type ascriptions like (3:ℚ); use ℚ/ℝ when dividing; write `¬ (P)`
with parentheses; do not use undefined identifiers; use `Fin 3 → Bool` predicates for logic."""


def _render_user(problem: str, steps: list[ReasoningStep], final: str | None) -> str:
    body = "\n".join(f"Step {s.index}: {s.text}" for s in steps)
    return f"PROBLEM:\n{problem}\n\nSTUDENT STEPS:\n{body}\nFINAL ANSWER: {final or '(none)'}"


def _clean_prop(p: str | None) -> str | None:
    if p is None:
        return None
    p = str(p).strip()
    if not p or p.lower() in {"null", "none", "skip"}:
        return None
    p = re.sub(r"^```(?:lean)?|```$", "", p, flags=re.M).strip()
    p = re.sub(r"^(theorem|lemma|example)\s+\w*\s*:\s*", "", p)
    p = re.sub(r"\s*:=\s*by.*$", "", p, flags=re.S)
    p = p.rstrip(" .")
    return p or None


def _outer_negation(prop: str) -> str | None:
    """If `prop` is `¬ (X)` with the parentheses spanning the whole rest, return X."""
    m = re.match(r"^¬\s*\((.*)\)$", prop, flags=re.S)
    if not m:
        return None
    depth = 0
    for ch in m.group(1):
        depth += (ch == "(") - (ch == ")")
        if depth < 0:
            return None
    return m.group(1).strip() if depth == 0 else None


def _top_level_split(s: str, sep: str) -> list[str]:
    parts, depth, cur = [], 0, []
    i = 0
    while i < len(s):
        ch = s[i]
        depth += (ch == "(") - (ch == ")")
        if depth == 0 and s.startswith(sep, i):
            parts.append("".join(cur).strip())
            cur = []
            i += len(sep)
            continue
        cur.append(ch)
        i += 1
    parts.append("".join(cur).strip())
    return parts


def degenerate_inference(prop: str) -> bool:
    """True if the (un-negated) inference concludes one of its own premises, e.g.
    `∀ (y k : ℤ), y > k ∧ y > k → y > k` — a formalizer artefact, never a real question."""
    inner = _outer_negation(prop) or prop
    body = re.sub(r"^∀\s*[^,]*,\s*", "", inner.strip())
    chain = _top_level_split(body, "→")
    if len(chain) < 2:
        return False
    concl = _norm_atom(chain[-1])
    premises = {_norm_atom(c) for p in chain[:-1] for c in _top_level_split(p, "∧")}
    return concl in premises


@dataclass(frozen=True)
class Signature:
    """Coarse semantic shape shared by a question and its formalization: does the claim
    involve a two-place relation, is that relation symmetric, which counts does it hinge on."""

    binary: bool
    symmetric: bool
    counts: frozenset[int]


_BINARY_TYPES = re.compile(
    r"Fin\s*\d+\s*→\s*Fin\s*\d+\s*→\s*(?:Bool|Prop)|(\w+)\s*→\s*\1\s*→\s*(?:Bool|Prop)"
)
_ORDER_REL = re.compile(r"[<>≤≥]")
_INT_BINDERS = re.compile(r":\s*[ℤℕℚℝ]")
_SYMMETRIC_MARKERS = re.compile(
    r"FalconVerifier\.(?:Regular|IsGraph)|(\w+)\s+(\w+)\s+(\w+)\s*=\s*\1\s+\3\s+\2"
)


def prop_signature(prop: str) -> Signature:
    """Read the `Signature` off a Lean proposition mechanically: a `Fin n → Fin n → Bool`
    binder or an ordering over ℤ/ℕ is a binary relation; `FalconVerifier.Regular` or an explicit
    `f x y = f y x` marks symmetry; numeric literals are the available counts."""
    binary = bool(_BINARY_TYPES.search(prop)) or bool(
        _INT_BINDERS.search(prop) and _ORDER_REL.search(prop)
    )
    symmetric = bool(_SYMMETRIC_MARKERS.search(prop))
    counts = frozenset(int(n) for n in re.findall(r"(?<![\w.])(\d+)(?![\w.])", prop))
    return Signature(binary=binary, symmetric=symmetric, counts=counts)


def compare_signatures(question: Signature, formal: Signature) -> tuple[bool, str]:
    """Deterministic faithfulness verdict. Only *structure loss* is rejected: a binary relation
    the question is about that the formula does not have, symmetry that was dropped, or a
    structural count that never appears in the formula."""
    if question.binary and not formal.binary:
        return (
            False,
            "round-trip: question is about a relation between individuals, formula has none",
        )
    if question.symmetric and formal.binary and not formal.symmetric:
        return False, "round-trip: mutual relation formalized without symmetry"
    missing = sorted(c for c in question.counts if not {c, c + 1} & formal.counts)
    if question.binary and missing:
        return False, f"round-trip: structural count(s) {missing} absent from the formula"
    return True, "round-trip signature matches"


def _norm_atom(s: str) -> str:
    s = re.sub(r"\s+", "", s)
    while s.startswith("(") and s.endswith(")") and _outer_negation("¬" + s) is not None:
        s = s[1:-1]
    return s


def align_polarity(prop: str | None, final: str | None) -> str | None:
    """Make a yes/no `problem_prop` assert the student's stated answer.

    The prompt asks for `¬ (…)` when the answer is No; LLM formalizers frequently drop the
    negation and encode the *valid* inference instead, so a wrong “No” is then “verified”.
    Only quantified/implicational props (logic questions) are touched; arithmetic props
    already carry the answer as a literal.
    """
    pol = yes_no_polarity(final)
    if prop is None or pol is None or not re.search(r"[∀∃→]", prop):
        return prop
    inner = _outer_negation(prop)
    if pol and inner is not None:
        return inner
    if not pol and inner is None:
        return f"¬ ({prop})"
    return prop


_PROBLEM_SLOT = "\x00problem_prop"


class Formalizer:
    def __init__(self, model: ChatModel, max_tokens: int = 2500, memory: Memory | None = None):
        self.model = model
        self.max_tokens = max_tokens
        self.memory = memory
        self._problem_hit: tuple[str, str] | None = None
        self._certified: dict[int, FormalStep] = {}
        self.last_memory_hits = 0

    def _recall_step(self, problem: str, step: ReasoningStep) -> FormalStep | None:
        if self.memory is None:
            return None
        hit = self.memory.get_formalization(self.model.model, problem, step.text)
        if hit is None:
            return None
        note = f"memory: {hit.note}" if hit.note else "memory: formalization reused"
        return FormalStep(index=step.index, kind=hit.kind, lean_prop=hit.lean_prop, note=note[:200])

    def _recall_problem(self, problem: str, final: str | None) -> str | None:
        if self.memory is None:
            return None
        hit = self.memory.get_formalization(
            self.model.model, problem, f"{_PROBLEM_SLOT}|{final or ''}"
        )
        return hit.lean_prop if hit else None

    def remember(
        self,
        problem: str,
        steps: list[ReasoningStep],
        final: str | None,
        form: Formalization,
        report: VerificationReport,
    ) -> None:
        """Store LLM-produced translations that type-checked, so the same sentence of the
        same problem is never sent to the model twice."""
        if self.memory is None or form.raw == "pregroup":
            return
        verdict_by_index = {s.index: s.verdict for s in report.steps}
        text_by_index = {s.index: s.text for s in steps}
        for fs in form.steps:
            if fs.note.startswith(("pregroup:", "memory:")):
                continue
            if verdict_by_index.get(fs.index) == Verdict.ILL_FORMED:
                continue
            step_text = text_by_index.get(fs.index)
            if step_text:
                self.memory.put_formalization(
                    self.model.model, problem, step_text, fs.lean_prop, fs.kind, fs.note
                )
        if (
            form.problem_prop
            and not form.problem_note.startswith("pregroup:")
            and report.final_answer_verdict != Verdict.ILL_FORMED
        ):
            self.memory.put_formalization(
                self.model.model,
                problem,
                f"{_PROBLEM_SLOT}|{final or ''}",
                form.problem_prop,
                "problem",
                "",
            )

    def _messages(self, problem: str, steps: list[ReasoningStep], final: str | None):
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": FEWSHOT_USER},
            {"role": "assistant", "content": FEWSHOT_ASSISTANT},
            {"role": "user", "content": FEWSHOT_USER2},
            {"role": "assistant", "content": FEWSHOT_ASSISTANT2},
            {"role": "user", "content": _render_user(problem, steps, final)},
        ]

    def formalize(
        self, problem: str, steps: list[ReasoningStep], final: str | None
    ) -> tuple[Formalization, list[dict[str, str]]]:
        """Grammar first, LLM second.

        Steps inside the pregroup fragment (Arabic or symbolic arithmetic) are translated
        deterministically with a derivation certificate (`note="pregroup: ..."`); only the
        remaining steps (and the problem claim, if the grammar could not parse the
        question) are sent to the LLM.
        """
        self.last_memory_hits = 0
        grammar: dict[int, FormalStep] = {}
        for s in steps:
            hit = arabic.formalize_step(s.text)
            if hit:
                prop, deriv = hit
                grammar[s.index] = FormalStep(
                    index=s.index, kind="arith", lean_prop=prop, note=f"pregroup: {deriv}"
                )
                continue
            recalled = self._recall_step(problem, s)
            if recalled is not None:
                grammar[s.index] = recalled
                self.last_memory_hits += 1
        problem_hit = (
            arabic.formalize_problem(problem, final)
            or arabic_logic.formalize_logic_problem(problem)
            or arabic_graph.formalize_graph_problem(problem)
        )
        self._problem_hit = problem_hit
        self._certified = grammar
        recalled_problem = None if problem_hit else self._recall_problem(problem, final)
        if recalled_problem is not None:
            self.last_memory_hits += 1

        if len(grammar) == len(steps) and problem_hit:
            form = Formalization(
                problem_prop=align_polarity(problem_hit[0], final),
                problem_note=f"pregroup: {problem_hit[1]}",
                steps=[grammar[s.index] for s in steps],
                raw="pregroup",
            )
            return form, self._messages(problem, steps, final)

        pending = [s for s in steps if s.index not in grammar]
        if not pending and (problem_hit or recalled_problem is not None):
            form = Formalization(
                problem_prop=align_polarity(recalled_problem, final),
                problem_note="memory: problem claim reused",
                steps=[grammar[s.index] for s in steps],
                raw="memory",
            )
            return form, self._messages(problem, steps, final)

        messages = self._messages(problem, pending or steps, final)
        resp = self.model.chat(messages, temperature=0.0, max_tokens=self.max_tokens)
        messages.append({"role": "assistant", "content": resp.content})
        form = self._parse(resp.content, steps)
        form.latency_s = resp.latency_s
        form.steps = [grammar.get(fs.index, fs) for fs in form.steps]
        if problem_hit:
            form.problem_prop = problem_hit[0]
            form.problem_note = f"pregroup: {problem_hit[1]}"
        elif recalled_problem is not None:
            form.problem_prop = recalled_problem
            form.problem_note = "memory: problem claim reused"
        form.problem_prop = align_polarity(form.problem_prop, final)
        return form, messages

    def repair(
        self,
        messages: list[dict[str, str]],
        errors: dict[int | str, str],
        steps: list[ReasoningStep],
        final: str | None = None,
    ) -> tuple[Formalization, list[dict[str, str]]]:
        err_text = "\n".join(f"- step {k}: {v}" for k, v in errors.items())
        messages = messages + [{"role": "user", "content": REPAIR_PROMPT.format(errors=err_text)}]
        resp = self.model.chat(messages, temperature=0.0, max_tokens=self.max_tokens)
        messages.append({"role": "assistant", "content": resp.content})
        form = self._parse(resp.content, steps)
        form.latency_s = resp.latency_s
        form.steps = [self._keep_certified(fs) for fs in form.steps]
        if self._problem_hit:  # the grammar's problem claim is not up for LLM revision
            form.problem_prop = self._problem_hit[0]
            form.problem_note = f"pregroup: {self._problem_hit[1]}"
        form.problem_prop = align_polarity(form.problem_prop, final)
        return form, messages

    def _keep_certified(self, fs: FormalStep) -> FormalStep:
        """Grammar/memory steps carry a certificate; a repair round must not overwrite them."""
        kept = self._certified.get(fs.index)
        return kept if kept is not None else fs

    def audit(self, problem: str, step_text: str, prop: str) -> tuple[bool, str]:
        """Second-opinion check that `prop` faithfully encodes `step_text`."""
        msg = AUDIT_PROMPT.format(problem=problem, step=step_text, prop=prop)
        return self._audit_call(msg)

    def audit_yes_no(self, problem: str, answer: str, prop: str) -> tuple[bool, str]:
        """Audit the *content* of a yes/no `problem_prop`; polarity is checked mechanically."""
        if degenerate_inference(prop):
            return False, "degenerate inference: the conclusion is one of the premises"
        inner = _outer_negation(prop)
        msg = YESNO_AUDIT_PROMPT.format(
            problem=problem, answer=answer, prop=inner if inner is not None else prop
        )
        return self._audit_call(msg)

    def audit_roundtrip(
        self, problem: str, answer: str, prop: str, arabic: bool = False
    ) -> tuple[bool, str]:
        """Structured round-trip faithfulness check. The LLM only *extracts* a signature
        (binary relations, symmetry, structural counts) from the question; the signature of
        the Lean proposition is read off mechanically by `prop_signature`; the two are then
        compared deterministically. Catches the structure loss a free-form audit waves
        through — a binary relation flattened to a per-individual Bool, a dropped "exactly k"."""
        del answer, arabic
        resp = self.model.chat(
            [{"role": "user", "content": SIGNATURE_PROMPT.format(problem=problem)}],
            temperature=0.0,
            max_tokens=300,
        )
        try:
            raw = json.loads(extract_json(resp.content))
        except (json.JSONDecodeError, AttributeError):
            return True, "round-trip unavailable; kept"
        if not isinstance(raw, dict):
            return True, "round-trip unavailable; kept"
        rels = raw.get("binary_relations")
        counts = raw.get("counts")
        q = Signature(
            binary=bool(rels) if isinstance(rels, list) else False,
            symmetric=bool(raw.get("symmetric")),
            counts=frozenset(
                int(c) for c in counts if isinstance(c, int) and not isinstance(c, bool)
            )
            if isinstance(counts, list)
            else frozenset(),
        )
        return compare_signatures(q, prop_signature(prop))

    def _audit_call(self, msg: str) -> tuple[bool, str]:
        resp = self.model.chat([{"role": "user", "content": msg}], temperature=0.0, max_tokens=300)
        try:
            data = json.loads(extract_json(resp.content))
            return bool(data.get("faithful", True)), str(data.get("reason", ""))[:200]
        except (json.JSONDecodeError, AttributeError):
            return True, "audit unparsable; kept"

    @staticmethod
    def _parse(text: str, steps: list[ReasoningStep]) -> Formalization:
        try:
            data = json.loads(extract_json(text))
        except json.JSONDecodeError:
            log.warning("formalizer returned non-JSON; treating all steps as skipped")
            return Formalization(
                problem_prop=None,
                steps=[FormalStep(index=s.index, kind="skip", lean_prop=None) for s in steps],
                raw=text,
            )
        if isinstance(data, list):
            data = {"problem_prop": None, "steps": data}
        by_index: dict[int, FormalStep] = {}
        for item in data.get("steps", []) or []:
            try:
                idx = int(item.get("index"))
            except (TypeError, ValueError):
                continue
            prop = _clean_prop(item.get("lean_prop"))
            kind = str(item.get("kind", "arith" if prop else "skip"))
            if prop is None:
                kind = "skip"
            by_index[idx] = FormalStep(
                index=idx, kind=kind, lean_prop=prop, note=str(item.get("note", ""))[:200]
            )
        ordered = [
            by_index.get(s.index, FormalStep(index=s.index, kind="skip", lean_prop=None))
            for s in steps
        ]
        return Formalization(
            problem_prop=_clean_prop(data.get("problem_prop")), steps=ordered, raw=text
        )
