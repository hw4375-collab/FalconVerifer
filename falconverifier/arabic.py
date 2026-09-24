"""Arabic support: script detection, digit normalisation, and a pregroup-grammar
pre-formalizer for the arithmetic fragment of Arabic maths talk.

Why a grammar and not only an LLM?  For Arabic the LLM formalizer is the weakest link:
Falcon's Arabic steps mix Eastern/Western digits, VSO/SVO orders and verb-incorporated
subjects.  A pregroup grammar (Lambek 1999; Bargelli & Lambek 2003 for Arabic) gives a
*deterministic* translation with an explicit derivation certificate: the sentence's type
string must contract to the sentence type `s`, and the contraction links tell us exactly
how the words' meanings compose (DisCoCat: Coecke, Sadrzadeh & Clark 2010).  When the
grammar parses a step we obtain a Lean `Prop` that is faithful *by construction* and skip
the LLM audit entirely.  Steps outside the fragment fall back to the LLM formalizer.

Pregroup types are strings of simple types `a`, `aˡ`, `aʳ`; the only rules used are the
contractions `aˡ a → 1` and `a aʳ → 1` (as in Bargelli–Lambek's Arabic fragment, iterated
adjoints are not needed).  Basic types: `n` (number phrase), `s` (declarative sentence),
`q` (question).

Morphology caveat (proved in lean/FalconVerifier/Arabic/Semantics.lean): pregroup types
that do not index person/gender/number silently accept agreement violations; every lexical
entry below therefore carries a `feat` record that the semantics keeps, and the parser
refuses to link a subject wire whose features clash with the verb's.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction

# ---------------------------------------------------------------- script / digits

_ARABIC_LETTER = re.compile(r"[\u0621-\u064A\u0660-\u0669\u06F0-\u06F9]")
_EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def is_arabic(text: str) -> bool:
    letters = [c for c in text if c.isalpha() or c.isdigit()]
    if not letters:
        return False
    return sum(1 for c in letters if _ARABIC_LETTER.match(c)) / len(letters) > 0.3


def normalize_digits(text: str) -> str:
    """Eastern Arabic digits and separators -> ASCII (٣٬٥٠٠٫٢٥ -> 3500.25)."""
    return text.translate(_EASTERN_DIGITS).replace("٫", ".").replace("٬", "").replace("٪", "%")


# ---------------------------------------------------------------- pregroup kernel


@dataclass(frozen=True)
class Simple:
    base: str  # 'n' | 's' | 'q'
    adj: int  # 0 plain, -1 left adjoint (ˡ), +1 right adjoint (ʳ)

    def __str__(self) -> str:
        return self.base + {0: "", -1: "ˡ", 1: "ʳ"}[self.adj]


def _parse_type(spec: str) -> list[Simple]:
    out: list[Simple] = []
    for tok in spec.split():
        if tok.endswith("ˡ"):
            out.append(Simple(tok[:-1], -1))
        elif tok.endswith("ʳ"):
            out.append(Simple(tok[:-1], 1))
        else:
            out.append(Simple(tok, 0))
    return out


@dataclass
class Entry:
    surface: str
    type: str  # pregroup type string, e.g. 'nʳ n nˡ'
    sem: str  # 'lit' | 'op:+' | 'op:*' | 'eq' | 'lt' | 'gt' | 'pct' | 'dvd' | 'ndvd' | 'q'
    feat: dict[str, str] = field(default_factory=dict)  # person/gender/number for verbs

    @property
    def simples(self) -> list[Simple]:
        return _parse_type(self.type)


# Lexicon for the arithmetic fragment.  Types follow Lambek's convention: an infix operator
# looks left for a number (`nʳ`), produces a number (`n`) and looks right for a number (`nˡ`).
# Arabic verbs are typed with their *incorporated* subject (Bargelli–Lambek §3): «يساوي»
# "it equals" is 3rd-sg-masc; its subject wire is the left number phrase.
LEXICON: list[Entry] = [
    # equality / copula ("يساوي" = it equals, "هو"/"هي" = is (pronoun copula), "تساوي" fem.)
    Entry("يساوي", "nʳ s nˡ", "eq", {"p": "3", "g": "m", "n": "sg"}),
    Entry("تساوي", "nʳ s nˡ", "eq", {"p": "3", "g": "f", "n": "sg"}),
    Entry("يعطي", "nʳ s nˡ", "eq", {"p": "3", "g": "m", "n": "sg"}),
    Entry("تعطي", "nʳ s nˡ", "eq", {"p": "3", "g": "f", "n": "sg"}),
    Entry("هو", "nʳ s nˡ", "eq", {"p": "3", "g": "m", "n": "sg"}),
    Entry("هي", "nʳ s nˡ", "eq", {"p": "3", "g": "f", "n": "sg"}),
    Entry("=", "nʳ s nˡ", "eq"),
    # comparison
    Entry("أكبر من", "nʳ s nˡ", "gt"),
    Entry("اكبر من", "nʳ s nˡ", "gt"),
    Entry("أصغر من", "nʳ s nˡ", "lt"),
    Entry("اصغر من", "nʳ s nˡ", "lt"),
    Entry(">", "nʳ s nˡ", "gt"),
    Entry("<", "nʳ s nˡ", "lt"),
    Entry("لا يساوي", "nʳ s nˡ", "ne"),
    Entry("≠", "nʳ s nˡ", "ne"),
    # divisibility: «١٢ يقبل القسمة على ٣» / «لا يقبل»
    Entry("يقبل القسمة على", "nʳ s nˡ", "dvd", {"p": "3", "g": "m", "n": "sg"}),
    Entry("قابل للقسمة على", "nʳ s nˡ", "dvd"),
    Entry("لا يقبل القسمة على", "nʳ s nˡ", "ndvd", {"p": "3", "g": "m", "n": "sg"}),
    Entry("غير قابل للقسمة على", "nʳ s nˡ", "ndvd"),
    # infix arithmetic operators
    Entry("زائد", "nʳ n nˡ", "op:+"),
    Entry("+", "nʳ n nˡ", "op:+"),
    Entry("ناقص", "nʳ n nˡ", "op:-"),
    Entry("-", "nʳ n nˡ", "op:-"),
    Entry("−", "nʳ n nˡ", "op:-"),
    Entry("ضرب", "nʳ n nˡ", "op:*"),
    Entry("مضروب في", "nʳ n nˡ", "op:*"),
    Entry("مضروبا في", "nʳ n nˡ", "op:*"),
    Entry("مضروباً في", "nʳ n nˡ", "op:*"),
    Entry("×", "nʳ n nˡ", "op:*"),
    Entry("*", "nʳ n nˡ", "op:*"),
    Entry("في", "nʳ n nˡ", "op:*"),  # «٣ في ٤» after ضرب/حاصل
    Entry("على", "nʳ n nˡ", "op:/"),
    Entry("تقسيم", "nʳ n nˡ", "op:/"),
    Entry("مقسوما على", "nʳ n nˡ", "op:/"),
    Entry("مقسوماً على", "nʳ n nˡ", "op:/"),
    Entry("÷", "nʳ n nˡ", "op:/"),
    Entry("/", "nʳ n nˡ", "op:/"),
    # percentage «٥٠٪ من ١٥٠»: "% of" — «من» after a percent literal multiplies by /100
    Entry("من", "nʳ n nˡ", "pct"),
    # prefix (VSO-like) functional nouns: «مجموع ٣ و ٤», «حاصل ضرب ٣ في ٤», «ناتج ...»
    Entry("مجموع", "n nˡ", "pre:+"),
    Entry("حاصل جمع", "n nˡ", "pre:+"),
    Entry("حاصل ضرب", "n nˡ", "pre:*"),
    Entry("ناتج ضرب", "n nˡ", "pre:*"),
    Entry("ناتج", "n nˡ", "pre:id"),
    Entry("العدد", "n nˡ", "pre:id", {"g": "m", "n": "sg"}),  # «العدد ١٢ يقبل ...»
    Entry("المجموع", "n nˡ", "pre:id", {"g": "m", "n": "sg"}),
    Entry("النتيجة", "n nˡ", "pre:id", {"g": "f", "n": "sg"}),
    Entry("القيمة", "n nˡ", "pre:id", {"g": "f", "n": "sg"}),
    Entry("حاصل", "n nˡ", "pre:id"),
    Entry("نصف", "n nˡ", "pre:half"),
    Entry("ثلث", "n nˡ", "pre:third"),
    Entry("ربع", "n nˡ", "pre:quarter"),
    Entry("ضعف", "n nˡ", "pre:double"),
    Entry("و", "nʳ n nˡ", "op:+"),  # «مجموع ٣ و ٤» — conjunction inside a sum
    Entry("مربع", "n nˡ", "pre:sq"),
    Entry("الجذر التربيعي ل", "n nˡ", "pre:sqrt"),
    # question words -> type q, looking right for a number phrase
    Entry("ما هو", "q nˡ", "q"),
    Entry("ما هي", "q nˡ", "q"),
    Entry("ما", "q nˡ", "q"),
    Entry("كم يساوي", "q nˡ", "q"),
    Entry("كم", "q nˡ", "q"),
    Entry("احسب", "q nˡ", "q"),
    Entry("أوجد", "q nˡ", "q"),
    Entry("اوجد", "q nˡ", "q"),
]

_BY_SURFACE: dict[str, list[Entry]] = {}
for _e in LEXICON:
    _BY_SURFACE.setdefault(_e.surface, []).append(_e)
_MAX_WORDS = max(len(s.split()) for s in _BY_SURFACE)

_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?%?$")
_NOISE = {
    "إذن",
    "إذا",
    "لذلك",
    "أي",
    "اذن",
    "لذا",
    "ثم",
    "الآن",
    "نحصل",
    "نجد",
    "أن",
    "ان",
    "بالتالي",
}
_PUNCT = re.compile(r"[،,؛;:؟?!.]+$")


@dataclass
class Word:
    surface: str
    entry: Entry
    simples: list[Simple]
    value: Fraction | None = None
    percent: bool = False


def tokenize(text: str) -> list[str]:
    text = normalize_digits(text)
    text = re.sub(r"([=+×*÷/<>≠()−-])", r" \1 ", text)
    text = re.sub(r"(\d)\s*%", r"\1%", text)
    toks = [t for t in text.split() if t]
    # strip trailing Arabic punctuation and definite article on lexical heads
    out = []
    for t in toks:
        t = _PUNCT.sub("", t)
        if t and t not in _NOISE:
            out.append(t)
    return out


def _lex(tokens: list[str]) -> list[list[Word]] | None:
    """Greedy longest-match lexical lookup; returns per-position candidate words."""
    words: list[list[Word]] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if _NUM_RE.match(tok):
            pct = tok.endswith("%")
            val = Fraction(tok.rstrip("%"))
            words.append(
                [Word(tok, Entry(tok, "n", "lit"), [Simple("n", 0)], value=val, percent=pct)]
            )
            i += 1
            continue
        if tok in {"(", ")"}:
            e = Entry(tok, "n nˡ" if tok == "(" else "nʳ n", "lpar" if tok == "(" else "rpar")
            words.append([Word(tok, e, e.simples)])
            i += 1
            continue
        matched = False
        for span in range(min(_MAX_WORDS, len(tokens) - i), 0, -1):
            phrase = " ".join(tokens[i : i + span])
            cands = _BY_SURFACE.get(phrase) or _BY_SURFACE.get(phrase.lstrip("ال"))
            if cands:
                words.append([Word(phrase, e, e.simples) for e in cands])
                i += span
                matched = True
                break
        if not matched:
            return None
    return words


@dataclass
class Parse:
    words: list[Word]
    links: list[tuple[int, int]]  # (position of adjoint wire, position of plain wire)
    lean_prop: str | None
    result_type: str
    derivation: str


def _contractible(a: Simple, b: Simple) -> bool:
    return a.base == b.base and ((a.adj == -1 and b.adj == 0) or (a.adj == 0 and b.adj == 1))


def _reduce(
    simples: list[tuple[int, Simple]],
) -> tuple[list[tuple[int, Simple]], list[tuple[int, int]]]:
    """Find a contraction-only reduction of the type string to a single basic type.

    Contractions `aˡ a → 1`, `a aʳ → 1` are non-crossing links, so the search is the
    classic O(n³) planar-matching recursion (memoised); greedy left-to-right fails on
    prefix heads such as «ناتج ١٧ × ٢٣» where the head's `nˡ` must skip the first literal
    and link to the operator's output."""
    n = len(simples)
    memo: dict[tuple[int, int], list[tuple[int, int]] | None] = {}

    def empty(i: int, j: int) -> list[tuple[int, int]] | None:
        if i >= j:
            return []
        key = (i, j)
        if key in memo:
            return memo[key]
        res = None
        a = simples[i][1]
        for k in range(i + 1, j):
            if _contractible(a, simples[k][1]):
                inner = empty(i + 1, k)
                if inner is None:
                    continue
                outer = empty(k + 1, j)
                if outer is None:
                    continue
                res = [(i, k)] + inner + outer
                break
        memo[key] = res
        return res

    for m in range(n):
        if simples[m][1].adj != 0:
            continue
        left = empty(0, m)
        if left is None:
            continue
        right = empty(m + 1, n)
        if right is None:
            continue
        links = [(simples[a][0], simples[b][0]) for a, b in left + right]
        return [simples[m]], links
    return simples, []


def _assemble(words: list[Word]) -> tuple[str, str] | None:
    """Build the meaning term along the pregroup wiring and render it as Lean.

    Returns (lean_prop_or_expr, kind) where kind ∈ {'s','n','q'}."""
    # Number-phrase expressions: operator-precedence over the flat word list is exactly the
    # semantics the contraction links induce for the `nʳ n nˡ` infix types.
    rel = [w for w in words if w.entry.type.startswith("nʳ s")]
    if len(rel) > 1:
        return None
    if rel:
        k = words.index(rel[0])
        if not _agrees(words[:k], rel[0]):
            return None
        lhs, rhs = _expr(words[:k]), _expr(words[k + 1 :])
        if lhs is None or rhs is None:
            return None
        sem = rel[0].entry.sem
        if sem == "eq":
            return f"{lhs} = {rhs}", "s"
        if sem == "ne":
            return f"{lhs} ≠ {rhs}", "s"
        if sem == "gt":
            return f"{lhs} > {rhs}", "s"
        if sem == "lt":
            return f"{lhs} < {rhs}", "s"
        if sem in {"dvd", "ndvd"}:
            l_int, r_int = lhs.replace(":ℚ", ":ℤ"), rhs.replace(":ℚ", ":ℤ")
            return (f"{r_int} ∣ {l_int}" if sem == "dvd" else f"¬ ({r_int} ∣ {l_int})"), "s"
        return None
    if words and words[0].entry.sem == "q":
        e = _expr(words[1:])
        return (e, "q") if e else None
    e = _expr(words)
    return (e, "n") if e else None


def _agrees(subject: list[Word], verb: Word) -> bool:
    """Subject–verb agreement: the head noun of the subject phrase must match the verb's
    gender feature. The bare pregroup types accept «العدد ١٢ تساوي ٣» (masc. noun, fem. verb);
    the feature record is what rejects it — cf. `indexed_rejects_bad_agreement` in Lean."""
    vg = verb.entry.feat.get("g")
    if vg is None:
        return True
    heads = [w for w in subject if w.entry.feat.get("g")]
    return not heads or heads[0].entry.feat["g"] == vg


_PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "pct": 2}


class _ExprParser:
    """Recursive descent over the number fragment (mirrors the `nʳ n nˡ` wiring).

    Literals are ascribed ℚ so `/` and `-` are exact (see verifier.lift_to_rat for why).
    Prefix heads («مجموع», «نصف», «ضعف» …) scope over the whole following phrase, as their
    `n nˡ` type dictates — the incoming wire is the entire reduced number phrase."""

    def __init__(self, words: list[Word]):
        self.w = words
        self.i = 0
        self.first = True

    def peek(self) -> Word | None:
        return self.w[self.i] if self.i < len(self.w) else None

    def parse(self) -> str | None:
        try:
            e = self.expr(0)
        except _Bad:
            return None
        return e if self.i == len(self.w) else None

    def expr(self, min_prec: int) -> str:
        lhs = self.atom()
        while True:
            w = self.peek()
            if w is None or not (w.entry.sem.startswith("op:") or w.entry.sem == "pct"):
                return lhs
            op = w.entry.sem[3:] if w.entry.sem.startswith("op:") else "pct"
            if _PREC[op] < min_prec:
                return lhs
            self.i += 1
            rhs = self.expr(_PREC[op] + 1)
            if op == "pct":
                lhs = f"{lhs} / 100 * {_par(rhs)}"
            elif _PREC[op] == 1:
                lhs = f"{lhs} {op} {rhs}"
            else:
                lhs = f"{_par(lhs)} {op} {_par(rhs)}"

    def atom(self) -> str:
        w = self.peek()
        if w is None:
            raise _Bad
        self.i += 1
        sem = w.entry.sem
        if sem == "lit":
            lit = f"({_fmt(w.value)}:ℚ)" if self.first else _fmt(w.value)
            self.first = False
            return lit
        if sem == "lpar":
            e = self.expr(0)
            nxt = self.peek()
            if nxt is None or nxt.entry.sem != "rpar":
                raise _Bad
            self.i += 1
            return f"({e})"
        if sem.startswith("pre:"):
            return _prefix(sem[4:], self.expr(0))
        raise _Bad


class _Bad(Exception):
    pass


def _expr(words: list[Word]) -> str | None:
    return _ExprParser(words).parse()


def _par(x: str) -> str:
    return (
        f"({x})" if " " in x and not (x.startswith("(") and x.endswith(")") and _balanced(x)) else x
    )


def _balanced(x: str) -> bool:
    depth = 0
    for i, c in enumerate(x):
        depth += (c == "(") - (c == ")")
        if depth == 0 and i < len(x) - 1:
            return False
    return depth == 0


def _prefix(kind: str, arg: str) -> str:
    return {
        "id": arg,
        "+": arg,
        "*": arg,
        "half": f"{_par(arg)} / 2",
        "third": f"{_par(arg)} / 3",
        "quarter": f"{_par(arg)} / 4",
        "double": f"2 * {_par(arg)}",
        "sq": f"{_par(arg)} ^ 2",
        "sqrt": f"Real.sqrt {_par(arg)}",
    }[kind]


def _fmt(v: Fraction | None) -> str:
    if v is None:
        return "0"
    if v.denominator == 1:
        return str(v.numerator)
    return str(float(v))


def parse(text: str) -> Parse | None:
    """Parse one Arabic arithmetic sentence; None if outside the fragment or ungrammatical."""
    tokens = tokenize(text)
    if not tokens:
        return None
    cands = _lex(tokens)
    if cands is None:
        return None
    # try lexical ambiguity choices (small): pick first assignment whose types reduce
    choice = [c[0] for c in cands]
    simples = [(i, s) for i, w in enumerate(choice) for s in w.simples]
    stack, links = _reduce(simples)
    if len(stack) != 1 or stack[0][1].adj != 0:
        return None
    result = stack[0][1].base
    assembled = _assemble(choice)
    if assembled is None:
        return None
    prop, kind = assembled
    if kind != result:
        return None
    deriv = " ".join(str(s) for _, s in simples) + f" → {result}"
    return Parse(choice, links, prop, result, deriv)


def formalize_step(text: str) -> tuple[str, str] | None:
    """Return (lean_prop, derivation) for a declarative Arabic arithmetic step, else None."""
    p = parse(text)
    if p and p.result_type == "s" and p.lean_prop:
        return p.lean_prop, p.derivation
    return None


def formalize_problem(problem: str, final_answer: str | None) -> tuple[str, str] | None:
    """«ما هو ناتج ١٧ × ٢٣؟» + FINAL ANSWER 391 -> `(17:ℚ) * 23 = 391`."""
    if final_answer is None:
        return None
    ans = normalize_digits(final_answer).split("=")[-1]
    m = re.search(r"-?\d+(?:\.\d+)?", ans.replace(",", ""))
    if not m:
        return None
    p = parse(problem)
    if p and p.result_type == "q" and p.lean_prop:
        return f"{p.lean_prop} = {m.group(0)}", p.derivation
    return None
