"""Deterministic fragment for Arabic *quantity narratives* (word problems).

A narrative is a sequence of clauses, each acting on one running quantity:

    يبلغ سعر هاتف ٨٠٠ درهماً.           state := 800
    خُفِّض بنسبة ١٠٪                       state := state · (1 − 10/100)
    ثم خُفِّض السعر الجديد بنسبة ٢٠٪ أخرى. state := state · (1 − 20/100)
    ما هو السعر النهائي؟                   ask state

Each clause is a lexicalised pattern with numeric slots; the semantics is a total function
on the state (a ℚ expression rendered verbatim into Lean).  The Lean proposition asserts
`⟨expression⟩ = ⟨student's final answer⟩`, so the kernel decides it by `norm_num` — no LLM
is involved and the certificate lists the clauses that fired, in order.

Only narratives whose *every* clause is recognised are formalised; anything else returns
None and falls through to the LLM formalizer, so this module never guesses.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from .arabic import normalize_digits

_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")
_NUM = r"(\d+(?:\.\d+)?)"
_NUMX = r"\d+(?:\.\d+)?"
_W = r"[^\s،.؛]+"  # one Arabic word (name, item noun, …)

Op = Callable[[str, list[str]], str]


@dataclass(frozen=True)
class Clause:
    name: str
    pattern: re.Pattern[str]
    apply: Op  # (state, groups) -> new state (Lean ℚ expression), '' state = none yet


def _lit(n: str) -> str:
    return f"({n}:ℚ)"


def _par(x: str) -> str:
    return x if re.fullmatch(r"\(.*\)|\d+(?:\.\d+)?", x) else f"({x})"


def _pct_factor(p: str, sign: str) -> str:
    return f"(1 {sign} {p} / 100)"


_CLAUSES: list[Clause] = [
    # ── openers ────────────────────────────────────────────────────────────────
    Clause(
        "price",
        re.compile(
            rf"^(?:يبلغ|كان)?\s*سعر\s+{_W}\s+{_NUM}\s+(?:درهما|درهم|دولارا|دولار|ريالا|ريال)$"
        ),
        lambda st, g: _lit(g[0]),
    ),
    Clause(
        "boxes",
        re.compile(
            rf"^(?:اشترى|اشترت|لدى|عند)\s+{_W}\s+{_NUM}\s+(?:علبة|صندوقا|صندوق|كيسا|كيس|حقيبة)\s+(?:تحتوي|يحتوي)\s+كل\s+(?:منها|منه)\s+على\s+{_NUM}\s+{_W}$"
        ),
        lambda st, g: f"{_lit(g[0])} * {g[1]}",
    ),
    Clause(
        "have",
        re.compile(
            rf"^(?:لدينا|لدى\s+{_W}|عند\s+{_W}|كان\s+(?:لدى|مع)\s+{_W})\s+{_NUM}\s+{_W}(?:\s+نضعها\s+في\s+صناديق\s+تتسع\s+كل\s+منها\s+{_NUM}\s+{_W})?$"
        ),
        lambda st, g: f"{_lit(g[0])} / {g[1]}" if g[1] else _lit(g[0]),
    ),
    Clause(
        "father_age",
        re.compile(
            rf"^عمر\s+الأب\s+(?:اليوم|الآن)?\s*{_NUM}\s+(?:أمثال|مرات|أضعاف|ضعف)\s+عمر\s+ابنه$"
        ),
        lambda st, g: f"{_lit(g[0])} * {{child}}",
    ),
    Clause(
        "child_age",
        re.compile(rf"^و?عمر\s+الابن\s+{_NUM}\s+(?:سنوات|سنة|عاما|أعوام)$"),
        lambda st, g: st.replace("{child}", g[0]),
    ),
    Clause(
        "purchase",
        re.compile(
            rf"^(?:اشترت|اشترى)\s+{_W}\s+{_NUM}\s+{_W}\s+بسعر\s+{_NUM}\s+(?:درهما|درهم)\s+{_W}\s+و\s*{_NUM}\s+{_W}\s+بسعر\s+{_NUM}\s+(?:درهما|درهم)\s+{_W}$"
        ),
        lambda st, g: f"{_lit(g[0])} * {g[1]} + {g[2]} * {g[3]}",
    ),
    Clause(
        "paid",
        re.compile(rf"^و?دفعت?\s+{_NUM}\s+(?:درهما|درهم)$"),
        lambda st, g: f"{_lit(g[0])} - {_par(st)}",
    ),
    Clause(
        "grades",
        re.compile(
            rf"^حصلت?\s+{_W}\s+على\s+الدرجات\s+((?:{_NUMX}\s*[،,و]\s*)+{_NUMX})\s+في\s+{_NUM}\s+(?:اختبارات|اختبار|امتحانات)$"
        ),
        lambda st, g: f"({' + '.join(_lit(v) for v in re.findall(_NUM, g[0]))}) / {g[1]}",
    ),
    Clause(
        "think_number",
        re.compile(rf"^فكر\s+{_W}\s+في\s+عدد$"),
        lambda st, g: "{x}",
    ),
    # ── operations on the running quantity ──────────────────────────────────────
    Clause(
        "discount",
        re.compile(
            rf"^(?:ثم\s+)?(?:خفض|انخفض|نقص|قل)\s*(?:سعره|السعر\s+الجديد|السعر|ثمنه)?\s*بنسبة\s+{_NUM}\s*%\s*(?:أخرى|إضافية)?$"
        ),
        lambda st, g: f"{_par(st)} * {_pct_factor(g[0], '-')}",
    ),
    Clause(
        "markup",
        re.compile(
            rf"^(?:ثم\s+)?(?:زاد|ارتفع|رفع)\s*(?:سعره|السعر\s+الجديد|السعر|ثمنه)?\s*بنسبة\s+{_NUM}\s*%\s*(?:أخرى|إضافية)?$"
        ),
        lambda st, g: f"{_par(st)} * {_pct_factor(g[0], '+')}",
    ),
    Clause(
        "give",
        re.compile(
            rf"^(?:ثم\s+)?(?:أعطى|أعطت|باع|باعت|فقد|فقدت|أكل|أكلت|استخدم|استخدمت|أنفق|أنفقت)\s+{_NUM}\s+{_W}(?:\s+من\s+مجموعها)?(?:\s+ل{_W})?$"
        ),
        lambda st, g: f"{_par(st)} - {g[0]}",
    ),
    Clause(
        "gain",
        re.compile(
            rf"^(?:ثم\s+)?(?:اشترى|اشترت|حصل\s+على|حصلت\s+على|أضاف|أضافت|وجد|وجدت)\s+{_NUM}\s+{_W}(?:\s+(?:أخرى|إضافية|أخر))?$"
        ),
        lambda st, g: f"{_par(st)} + {g[0]}",
    ),
    Clause(
        "times",
        re.compile(rf"^(?:ثم\s+)?ضربه\s+في\s+{_NUM}$"),
        lambda st, g: f"{_par(st)} * {g[0]}",
    ),
    Clause(
        "plus",
        re.compile(rf"^(?:ثم\s+)?(?:أضاف|زاد)\s+{_NUM}$"),
        lambda st, g: f"{_par(st)} + {g[0]}",
    ),
    Clause(
        "result_is",
        re.compile(rf"^ف?كانت\s+النتيجة\s+{_NUM}$"),
        lambda st, g: f"{st} = {g[0]}",
    ),
    Clause(
        "after_years",
        re.compile(
            rf"^كم\s+(?:سيكون|يكون)\s+عمر\s+الأب\s+بعد\s+{_NUM}\s+(?:سنوات|سنة|عاما|أعوام)$"
        ),
        lambda st, g: f"{_par(st)} + {g[0]}",
    ),
]

_BY_NAME = {c.name: c for c in _CLAUSES}

_QUESTION = re.compile(
    r"^(?:ما\s+هو|ما\s+هي|كم|احسب|أوجد)\b.*$|^كم\s+(?:سيكون|يكون)\s+عمر\s+الأب\b.*$"
)
_ASK_WHOLE_BOXES = re.compile(r"صندوقا?\s+ممتلئا?")
_ASK_ORIGINAL = re.compile(r"العدد\s+الأصلي")


@dataclass(frozen=True)
class Narrative:
    expr: str  # Lean ℚ (or ℕ) expression for the asked quantity
    fired: list[str]
    nat_div: bool = False
    unknown_x: bool = False  # equation in x (think-of-a-number): expr contains {x}

    def prop(self, answer: str) -> str:
        if self.unknown_x:
            return self.expr.replace("{x}", f"({answer}:ℚ)")
        if "." in answer and not self.nat_div:
            # a decimal answer is read as ≈ to its printed precision (84.33 for 253/3)
            tol = f"(1 / 10 ^ {len(answer.split('.')[1])} : ℚ)"
            return f"{self.expr} - {answer} < {tol} ∧ {answer} - {_par(self.expr)} < {tol}"
        return f"{self.expr} = {answer}"

    def certificate(self) -> str:
        return "clauses " + " → ".join(self.fired) + f" ⇒ {self.expr}"


def _clean(text: str) -> str:
    text = normalize_digits(_DIACRITICS.sub("", text))
    return re.sub(r"\s+", " ", text).strip()


def _split(text: str) -> list[str]:
    # «،» inside a list of numbers («٨٥، ٩٠، ٧٨») is not a clause boundary
    parts = re.split(r"(?<!\d)،|،(?!\s*\d)|[.؛؟?!]|\s+ثم\s+", text)
    return [p.strip(" ،.") for p in parts if p and p.strip(" ،.")]


def analyze(problem: str) -> Narrative | None:
    text = _clean(problem)
    clauses = _split(text)
    if len(clauses) < 2:
        return None
    question = clauses[-1]
    if not _QUESTION.match(question):
        return None
    body = clauses[:-1]
    state = ""
    fired: list[str] = []
    if _BY_NAME["after_years"].pattern.match(question):  # the question adds the years
        body = body + [question]
    for cl in body:
        for c in _CLAUSES:
            m = c.pattern.match(cl)
            if m:
                state = c.apply(state, [g if g is not None else "" for g in m.groups()])
                fired.append(c.name)
                break
        else:
            return None
    if not state or "{child}" in state:
        return None
    unknown_x = "{x}" in state
    if unknown_x and (" = " not in state or not _ASK_ORIGINAL.search(question)):
        return None
    nat_div = bool(_ASK_WHOLE_BOXES.search(question))
    if nat_div:
        state = re.sub(r"\((\d+):ℚ\) / (\d+)$", r"(\1:ℕ) / \2", state)
        if ":ℕ" not in state:
            return None
    return Narrative(state, fired, nat_div, unknown_x)


def formalize_word_problem(problem: str, final_answer: str | None) -> tuple[str, str] | None:
    """`(93:ℚ) * 37 - 391 = 3050` plus a clause certificate, or None outside the fragment."""
    if final_answer is None:
        return None
    ans = normalize_digits(final_answer).split("=")[-1].replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", ans)
    if not m:
        return None
    nar = analyze(problem)
    if nar is None:
        return None
    if nar.nat_div and "." in m.group(0):
        return None
    return nar.prop(m.group(0)), nar.certificate()
