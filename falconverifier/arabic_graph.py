"""Deterministic Arabic *counting* fragment: symmetric binary relations and the handshake lemma.

The logic fragment (`arabic_logic.py`) only knows unary predicates («كل الأطباء متعلمون»), so
puzzles about a *relation* between people — friendship, handshakes, acquaintance — fell
through to the LLM formalizer, which tends to flatten the relation into a per-person Bool
and lose exactly the structure (symmetry, degree counting) the puzzle is about.

This module recognises the regular-graph family

    «n أشخاص، كل واحد منهم صديق لـ k من الآخرين بالضبط (والصداقة متبادلة)» …
    «هل يلزم أن أحدهم يكذب؟» / «هل يمكن ذلك؟»

and translates it, with a certificate, into

    ∃ f : Fin n → Fin n → Bool, FalconVerifier.Regular f k      («is it possible?»)
    ∀ f : Fin n → Fin n → Bool, ¬ FalconVerifier.Regular f k    («must someone be lying?»)

where `Regular` (lean/FalconVerifier/Graph.lean) says `f` is symmetric, irreflexive and every
vertex has exactly `k` neighbours. Lean settles the claim with the handshake lemma
(`no_regular_of_odd`, degree sum = 2·|edges|) or an explicit circulant witness — never by
enumerating the 2^(n²) relations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .arabic import normalize_digits

_DIACRITICS = re.compile(r"[\u064B-\u0652\u0670\u0640]")

NUMBER_WORDS = {
    "واحد": 1, "واحدا": 1, "واحدة": 1, "اثنان": 2, "اثنين": 2, "اثنتان": 2, "اثنتين": 2,
    "ثلاثة": 3, "ثلاث": 3, "اربعة": 4, "اربع": 4, "خمسة": 5, "خمس": 5, "ستة": 6, "ست": 6,
    "سبعة": 7, "سبع": 7, "ثمانية": 8, "ثماني": 8, "تسعة": 9, "تسع": 9, "عشرة": 10, "عشر": 10,
    "احد عشر": 11, "اثنا عشر": 12, "اثني عشر": 12, "ثلاثة عشر": 13, "اربعة عشر": 14,
    "خمسة عشر": 15, "ستة عشر": 16, "سبعة عشر": 17, "ثمانية عشر": 18, "تسعة عشر": 19,
    "عشرون": 20, "عشرين": 20,
}  # fmt: skip

# relation nouns/verbs whose real-world meaning is symmetric; the certificate records that
# symmetry was *assumed* from the lexeme (and «متبادلة» when the text says so explicitly)
_SYMMETRIC = {
    "صديق": "friendship",
    "اصدقاء": "friendship",
    "اصدقاؤه": "friendship",
    "اصدقائه": "friendship",
    "اصدقاءه": "friendship",
    "صداقة": "friendship",
    "الصداقة": "friendship",
    "يصافح": "handshake",
    "تصافح": "handshake",
    "صافح": "handshake",
    "مصافحة": "handshake",
    "مصافحات": "handshake",
    "المصافحة": "handshake",
    "يعرف": "acquaintance",
    "تعارف": "acquaintance",
    "التعارف": "acquaintance",
    "معارف": "acquaintance",
    "يتعارف": "acquaintance",
    "يلعب": "match",
    "مباراة": "match",
    "مباريات": "match",
}
_PEOPLE = {
    "اشخاص", "شخص", "طلاب", "طالب", "طالبا", "طالبة", "اصدقاء", "اطفال", "طفل", "لاعبين",
    "لاعبون", "لاعب", "ضيوف", "ضيف", "ضيفا", "زملاء", "افراد", "اعضاء", "رجال", "نساء", "فرق", "فريق",
    "فرقا",
}  # fmt: skip
_EACH = ("كل واحد", "كل شخص", "كل طالب", "كل لاعب", "كل ضيف", "كل فريق", "كل منهم", "كل فرد", "كل")
_REST = {"الباقين", "الاخرين", "المتبقين", "الباقيين"}
_LIE_Q = re.compile(
    r"هل\s+يلزم\s+(?:ان|انه)?\s*(?:واحدا|واحد|احدا|احد|احدهم|شخصا|شخص|طالبا|طالب)?.*?(?:يكذب|كاذب|كاذبا|مخطئ|مخطئا|غير\s+صادق)"
)
_POSSIBLE_Q = re.compile(r"هل\s+(?:يمكن|من\s+الممكن|يجوز|بالامكان|يعقل|يستقيم)")
_NECESSARY_LIE = re.compile(
    r"(?:يجب|لا\s*بد|بالضرورة)\s+ان\s+(?:يكون\s+)?(?:احدهم|واحدا?|شخصا?|احدا?)\s+(?:منهم\s+)?(?:على\s+الاقل\s+)?(?:يكذب|كاذب)"
)


def _norm(text: str) -> str:
    t = _DIACRITICS.sub("", normalize_digits(text))
    t = t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")
    t = re.sub(r"[،,؛;:؟?!.()«»\"']", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _numbers(text: str) -> list[tuple[int, int, str]]:
    """(position, value, surface) for every digit string or number word, in order."""
    out: list[tuple[int, int, str]] = []
    for m in re.finditer(r"\d+", text):
        out.append((m.start(), int(m.group()), m.group()))
    for word in sorted(NUMBER_WORDS, key=len, reverse=True):
        # optional clitic prefix: لثلاثة (to three), بثلاثة, وثلاثة, فثلاثة
        for m in re.finditer(rf"(?<![\w])[لبوف]?{re.escape(word)}(?![\w])", text):
            if not any(p <= m.start() < p + len(s) for p, _, s in out):
                out.append((m.start(), NUMBER_WORDS[word], m.group()))
    return sorted(out)


@dataclass
class GraphPuzzle:
    n: int
    k: int
    relation: str
    surfaces: dict[str, str]
    question: str  # "impossible" (someone lies) | "possible"
    explicit_symmetry: bool

    @property
    def n_surface(self) -> str:
        return self.surfaces["n"]

    @property
    def k_surface(self) -> str:
        return self.surfaces["k"]

    @property
    def exists_prop(self) -> str:
        return f"∃ f : Fin {self.n} → Fin {self.n} → Bool, FalconVerifier.Regular f {self.k}"

    @property
    def truth(self) -> bool:
        """Whether the yes-answer is correct: «someone lies» iff no k-regular graph on n
        vertices exists (n·k odd, or k ≥ n); «possible» iff one exists."""
        exists = self.k < self.n and (self.n * self.k) % 2 == 0
        return (not exists) if self.question == "impossible" else exists

    def prop(self) -> str:
        """Proposition asserting the *yes* answer, with no outer negation so that
        `align_polarity` can negate it for a «لا»."""
        if self.question == "impossible":
            return f"∀ f : Fin {self.n} → Fin {self.n} → Bool, ¬ FalconVerifier.Regular f {self.k}"
        return self.exists_prop

    def certificate(self) -> str:
        sym = (
            "symmetry stated («متبادلة»)"
            if self.explicit_symmetry
            else f"symmetry assumed from lexeme «{self.surfaces['relation']}»"
        )
        return (
            f"regular-graph fragment: n := {self.n_surface} ({self.n}); "
            f"k := {self.k_surface} ({self.k}); relation := {self.relation} ({sym}); "
            f"question := {self.question}; Lean: handshake lemma / circulant witness"
        )


def analyze(problem: str) -> GraphPuzzle | None:
    t = _norm(problem)
    rel_word = next((w for w in t.split() if w in _SYMMETRIC), None)
    if rel_word is None:
        return None
    if _LIE_Q.search(t) or _NECESSARY_LIE.search(t):
        question = "impossible"
    elif _POSSIBLE_Q.search(t):
        question = "possible"
    else:
        return None
    if not any(w in _PEOPLE for w in t.split()):
        return None
    # «… مع كل من الآخرين» is a complete graph, not «k of the others»: out of the fragment
    if re.search(r"(?:كل|جميع)\s+(?:من\s+)?(?:الاخرين|الباقين|المتبقين|البقية)", t):
        return None
    nums = _numbers(t)
    if len(nums) < 2:
        return None
    # n: the first number immediately followed by a people noun; k: the first number after
    # an «each»-phrase (or the first other number when «each» is implicit)
    n_hit = k_hit = None
    for pos, val, surf in nums:
        after = t[pos + len(surf) :].split()[:2]
        if n_hit is None and any(w in _PEOPLE for w in after):
            n_hit = (pos, val, surf)
            break
    if n_hit is None:
        return None
    each_end = next((m.end() for e in _EACH if (m := re.search(rf"(?<!\w){e}(?!\w)", t))), None)
    for pos, val, surf in nums:
        if pos == n_hit[0]:
            continue
        if each_end is not None and pos < each_end:
            continue
        # skip «الأربعة الباقين» (= n-1, a restatement) and «على الأقل واحد»
        after = t[pos + len(surf) :].split()[:2]
        if val == n_hit[1] - 1 and any(w in _REST for w in after):
            continue
        if t[max(0, pos - 12) : pos].rstrip().endswith("على الاقل") or "الاقل" in after:
            continue
        k_hit = (pos, val, surf)
        break
    if k_hit is None:
        return None
    n, k = n_hit[1], k_hit[1]
    if not (2 <= n <= 12 and 1 <= k <= 9):
        return None
    return GraphPuzzle(
        n=n,
        k=k,
        relation=_SYMMETRIC[rel_word],
        surfaces={"n": n_hit[2], "k": k_hit[2], "relation": rel_word},
        question=question,
        explicit_symmetry="متبادل" in t,
    )


def formalize_graph_problem(problem: str) -> tuple[str, str] | None:
    """Lean proposition asserting the *yes* answer, plus a certificate; None outside the
    fragment."""
    puz = analyze(problem)
    if puz is None:
        return None
    return puz.prop(), puz.certificate()


_REL_AR = {
    "friendship": "صداقة",
    "handshake": "مصافحة",
    "acquaintance": "معرفة",
    "match": "مباراة",
}


def explanation(problem: str, answered_yes: bool) -> str | None:
    """Arabic teaching text for a wrong yes/no answer in this fragment: the parity argument
    (degree sum = 2·edges) when the configuration is impossible, or an explicit witness
    when it is possible. None if the answer is right or the problem is outside the fragment."""
    puz = analyze(problem)
    if puz is None or answered_yes == puz.truth:
        return None
    n, k, rel = puz.n, puz.k, _REL_AR[puz.relation]
    exists = k < n and (n * k) % 2 == 0
    if not exists:
        if k >= n:
            return (
                f"لا يمكن أن يكون لكل شخص {k} من العلاقات ({rel}) بين {n} أشخاص فقط، "
                f"لأن كل شخص لديه {n - 1} من الآخرين على الأكثر."
            )
        return (
            f"برهان الزوجية (مبرهنة المصافحة): إذا كان لكل واحد من الـ{n} أشخاص {k} من "
            f"العلاقات ({rel})، فمجموع العلاقات المحسوبة من جهة كل شخص هو {n} × {k} = {n * k}. "
            f"لكن كل علاقة {rel} متبادلة فتُحسب مرتين (مرة من كل طرف)، فيجب أن يكون هذا المجموع "
            f"زوجياً = 2 × (عدد العلاقات). و{n * k} عدد فردي، فهذا تناقض؛ إذن لا يمكن أن يكون "
            f"الجميع صادقين. (Lean: `FalconVerifier.no_regular_of_odd`)"
        )
    # explicit witness: the circulant graph, described in words
    parts = [f"بمن يبعد عنه {d} في أي من الاتجاهين" for d in range(1, k // 2 + 1)]
    if k % 2 == 1:
        parts.append(f"بالشخص المقابل له (على بُعد {n // 2})")
    return (
        f"هذا الوضع ممكن فعلاً: رتّب الـ{n} أشخاص في دائرة، وليكن كل شخص على علاقة ({rel}) "
        f"{' و'.join(parts)}. فيكون لكل شخص بالضبط {k} من العلاقات، والعلاقة "
        f"متبادلة. (Lean: `FalconVerifier.circulant {n} {k}`)"
    )
