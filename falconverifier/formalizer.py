from __future__ import annotations

import json
import logging
import re

from . import arabic
from .llm import ChatModel, extract_json
from .schemas import Formalization, FormalStep, ReasoningStep
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
  named individual («خالد») becomes a bound variable `∀ (k : Fin 3), ...`, never an Arabic
  identifier.
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
the question, that it uses ∀/Fin/ℤ, or that the student's answer is short. Answer false ONLY
if a premise or the conclusion is missing, extra, or has different quantifier/negation
structure than the question, or the formula is degenerate (e.g. a premise repeated as the
conclusion, a trivially true or trivially false statement that ignores the question).

Question (may be Arabic): {problem}
Inference as formalized: {prop}

Answer with a JSON object: {{"faithful": true|false, "reason": "<one sentence>"}}"""

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


class Formalizer:
    def __init__(self, model: ChatModel, max_tokens: int = 2500):
        self.model = model
        self.max_tokens = max_tokens

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
        grammar: dict[int, FormalStep] = {}
        for s in steps:
            hit = arabic.formalize_step(s.text)
            if hit:
                prop, deriv = hit
                grammar[s.index] = FormalStep(
                    index=s.index, kind="arith", lean_prop=prop, note=f"pregroup: {deriv}"
                )
        problem_hit = arabic.formalize_problem(problem, final)

        if len(grammar) == len(steps) and problem_hit:
            form = Formalization(
                problem_prop=problem_hit[0],
                steps=[grammar[s.index] for s in steps],
                raw="pregroup",
            )
            return form, self._messages(problem, steps, final)

        messages = self._messages(problem, steps, final)
        resp = self.model.chat(messages, temperature=0.0, max_tokens=self.max_tokens)
        messages.append({"role": "assistant", "content": resp.content})
        form = self._parse(resp.content, steps)
        form.latency_s = resp.latency_s
        form.steps = [grammar.get(fs.index, fs) for fs in form.steps]
        if problem_hit:
            form.problem_prop = problem_hit[0]
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
        form.problem_prop = align_polarity(form.problem_prop, final)
        return form, messages

    def audit(self, problem: str, step_text: str, prop: str) -> tuple[bool, str]:
        """Second-opinion check that `prop` faithfully encodes `step_text`."""
        msg = AUDIT_PROMPT.format(problem=problem, step=step_text, prop=prop)
        return self._audit_call(msg)

    def audit_yes_no(self, problem: str, answer: str, prop: str) -> tuple[bool, str]:
        """Audit the *content* of a yes/no `problem_prop`; polarity is checked mechanically."""
        inner = _outer_negation(prop)
        msg = YESNO_AUDIT_PROMPT.format(
            problem=problem, answer=answer, prop=inner if inner is not None else prop
        )
        return self._audit_call(msg)

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
