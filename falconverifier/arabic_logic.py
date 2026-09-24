"""Deterministic Arabic *logic* fragment: syllogisms, propositional patterns and orderings.

The arithmetic fragment (`arabic.py`) gives every step a pregroup derivation; this module does
the same job for the yes/no logic questions of the benchmark («هل يلزم أن …؟»). It is a
small, explicit template grammar — not a general Arabic parser — and every translation carries
a certificate that lists the schema used for each sentence *and every lemma identification*
made across morphological variants (المربعات ≡ مربعات, طالب ≡ الطلاب, تبتل ≡ مبتلة).
Those identifications are exactly the step where Arabic morphology can mislead a coarse
grammar, so they are surfaced rather than hidden.

Encoding: finite model checking. Predicates are `Fin n → Bool`, propositions `Bool`,
individuals `Fin n`, comparatives `Fin m` with `>`; the inference is universally closed over
all of them, so Lean's `decide` settles it *and* its negation (the countermodel is found by
exhaustive search — syllogistic/propositional invalidity always has a tiny witness).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .arabic import normalize_digits

_DIACRITICS = re.compile(r"[\u064B-\u0652\u0670\u0640]")
_PUNCT = re.compile(r"[،,؛;:؟?!.]")

NAMES = {
    "سلطان", "خالد", "فاطمة", "أحمد", "عمر", "يوسف", "ليلى", "نور", "سارة", "محمد", "علي",
    "مريم", "زيد", "هند", "سعيد", "منى", "حسن", "ريم", "طارق", "أمل",
}  # fmt: skip
_QUANT_ALL = {"كل", "جميع", "كلّ"}
_QUANT_SOME = {"بعض"}
_NONE_HEADS = (("لا", "شيء", "من"), ("لا", "أحد", "من"), ("ليس", "أي", "من"))
_NEG = {"ليس", "ليست", "لم", "لا", "غير", "ليسوا"}
_COND = {"إذا", "اذا", "إن", "لو"}
_THEN = ("فإن", "فان", "فهو", "فهي", "فهم", "فإنه", "فإنها")
_PRODROP = {"أنه", "أنها", "انه", "انها", "إنه", "إنها", "فإنه", "فإنها", "أن", "إن", "فإن"}
_COPULA = {
    "كان",
    "كانت",
    "يكون",
    "تكون",
    "هو",
    "هي",
    "هم",
    "يجلس",
    "تجلس",
    "يقف",
    "تقف",
    "يقع",
    "تقع",
}
_CMP = {
    # surface -> (family, direction) ; direction +1: X R Y means X > Y
    ("أطول", "من"): ("height", 1),
    ("أقصر", "من"): ("height", -1),
    ("أكبر", "سناً", "من"): ("age", 1),
    ("أكبر", "سنا", "من"): ("age", 1),
    ("أصغر", "سناً", "من"): ("age", -1),
    ("أصغر", "سنا", "من"): ("age", -1),
    ("أكبر", "من"): ("age", 1),
    ("أصغر", "من"): ("age", -1),
    ("على", "يمين"): ("position", 1),
    ("على", "يسار"): ("position", -1),
}
_CMP_KEYS = sorted(_CMP, key=len, reverse=True)
_STOP = {"مباشرة", "تماماً", "تماما", "دائماً", "دائما", "أيضاً", "أيضا"}


def _norm(w: str) -> str:
    w = _DIACRITICS.sub("", normalize_digits(w))
    return w.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")


def skeleton(word: str) -> str:
    """Lemma-ish key: strip article, common suffixes, long vowels and one derivational
    prefix. Coarse on purpose; identifications are reported in the certificate."""
    w = _norm(word)
    if re.fullmatch(r"-?\d+(\.\d+)?", w):
        return w
    for pre in ("وال", "بال", "لل", "ال"):
        if w.startswith(pre) and len(w) > len(pre) + 2:
            w = w[len(pre) :]
            break
    for suf in ("ات", "ون", "ين", "ان", "ية", "يه", "ة", "ه", "ا", "ء", "ي"):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            w = w[: -len(suf)]
            break
    if w.endswith("ت") and len(w) > 3:  # perfect 3fs / 1s: أمطرت, درست
        w = w[:-1]
    w = re.sub(r"[اوي]", "", w)
    if len(w) >= 4 and w[0] in "متي":
        w = w[1:]
    return w or _norm(word)


@dataclass
class Clause:
    kind: str  # all | some | none | ind | prop | if | or | cmp
    args: tuple = ()
    neg: bool = False
    src: str = ""


@dataclass
class Certificate:
    schemas: list[str] = field(default_factory=list)
    idents: dict[str, list[str]] = field(default_factory=dict)

    def render(self) -> str:
        parts = list(self.schemas)
        for sym, surfaces in self.idents.items():
            if len(surfaces) > 1:
                parts.append(f"{sym} := " + " ≡ ".join(surfaces))
        return "; ".join(parts)


def _words(text: str) -> list[str]:
    text = _PUNCT.sub(" ", text)
    ws = [w for w in text.split() if w not in _STOP]
    return ws


def _split_sentences(problem: str) -> tuple[list[str], str] | None:
    p = normalize_digits(problem)
    p = re.sub(r"أجب\s+بنعم\s+أو\s+لا\.?", " ", p)
    m = re.search(r"هل\s+يلزم\s+(?:أن|ان)(?:ه|ها)?\s+(.*?)(?:[؟?]|$)", p)
    if not m:
        return None
    question = m.group(1).strip()
    body = p[: m.start()]
    sents = [s.strip() for s in re.split(r"[.،؟?]", body)]
    sents = [s for s in sents if s]
    if not sents:
        return None
    return sents, question


def _strip_lead(ws: list[str]) -> list[str]:
    ws = list(ws)
    while ws and ws[0] in _PRODROP:
        ws = ws[1:]
    if ws and ws[0].startswith("و") and len(ws[0]) > 1:
        rest = ws[0][1:]
        if rest in _QUANT_ALL | _QUANT_SOME | NAMES | _NEG or rest.isdigit() or rest in _COND:
            ws[0] = rest
        elif rest.startswith("ال") or len(rest) >= 3:
            ws[0] = rest
    while ws and ws[0] in _PRODROP:
        ws = ws[1:]
    return ws


def _is_name(w: str) -> bool:
    return w in NAMES or bool(re.fullmatch(r"\d+", w))


def _split_subject(ws: list[str]) -> tuple[list[str], list[str]] | None:
    """Subject = leading definite NP (ال-words, optional «في/من X» PP); predicate = rest."""
    i = 0
    while i < len(ws) and ws[i].startswith("ال"):
        i += 1
    if i == 0:
        return None
    if i + 1 < len(ws) and ws[i] in {"في", "من"}:
        i += 2
    if i >= len(ws):
        return None
    return ws[:i], ws[i:]


def _pred(ws: list[str]) -> tuple[bool, tuple[str, ...]]:
    neg = False
    ws = [w for w in ws if w not in _COPULA]
    if ws and ws[0] in _NEG:
        neg, ws = True, ws[1:]
    if ws and ws[0] == "يكن":
        ws = ws[1:]
    return neg, tuple(skeleton(w) for w in ws)


def _atom(ws: list[str]) -> tuple[bool, tuple[str, ...]]:
    """Propositional atom; negation may sit at position 0 or 1 («الأرض ليست مبتلة»)."""
    ws = _strip_lead([w for w in ws if w not in _COPULA])
    neg = False
    for i in range(min(2, len(ws))):
        if ws[i] in _NEG:
            neg, ws = True, ws[:i] + ws[i + 1 :]
            break
    if ws and ws[0] == "يكن":
        ws = ws[1:]
    return neg, tuple(skeleton(w) for w in ws)


def _find_cmp(ws: list[str]) -> tuple[int, int, str, int] | None:
    for key in _CMP_KEYS:
        for i in range(len(ws) - len(key) + 1):
            if tuple(ws[i : i + len(key)]) == key:
                fam, d = _CMP[key]
                return i, i + len(key), fam, d
    return None


def parse_clause(text: str) -> Clause | None:
    ws = _strip_lead(_words(text))
    if not ws:
        return None
    src = " ".join(ws)
    # none-quantifier
    for head in _NONE_HEADS:
        if tuple(ws[: len(head)]) == head:
            sp = _split_subject(ws[len(head) :])
            if not sp:
                return None
            neg, p = _pred(sp[1])
            return Clause("none", (tuple(skeleton(w) for w in sp[0]), p), neg, src)
    if ws[0] in _QUANT_ALL or ws[0] in _QUANT_SOME:
        sp = _split_subject(ws[1:])
        if not sp:
            return None
        neg, p = _pred(sp[1])
        kind = "all" if ws[0] in _QUANT_ALL else "some"
        return Clause(kind, (tuple(skeleton(w) for w in sp[0]), p), neg, src)
    if ws[0] in _COND:
        idx = next((i for i, w in enumerate(ws) if w.startswith(_THEN)), None)
        if idx is None or idx < 2:
            return None
        ant = _atom(ws[1:idx])
        cons = _atom(ws[idx + 1 :])
        if not ant[1] or not cons[1]:
            return None
        return Clause("if", (ant, cons), False, src)
    if ws[0] in {"إما", "اما"}:
        body = ws[1:]
        if "أو" not in body:
            return None
        j = body.index("أو")
        a, b = _atom(body[:j]), _atom(body[j + 1 :])
        if not a[1] or not b[1]:
            return None
        return Clause("or", (a, b), False, src)
    cmp_ = _find_cmp(ws)
    if cmp_:
        i, j, fam, d = cmp_
        left, right = (
            [w for w in ws[:i] if w not in _COPULA],
            [w for w in ws[j:] if w not in _COPULA],
        )
        if len(left) == 1 and len(right) == 1 and _is_name(left[0]) and _is_name(right[0]):
            x, y = (left[0], right[0]) if d > 0 else (right[0], left[0])
            return Clause("cmp", (fam, x, y), False, src)
        return None
    if _is_name(ws[0]) and len(ws) > 1:
        neg, p = _pred(ws[1:])
        if not p:
            return None
        return Clause("ind", (ws[0], p), neg, src)
    neg, a = _atom(ws)
    if not a:
        return None
    return Clause("prop", (a,), neg, src)


class _Symbols:
    """Assign Lean identifiers to predicates/atoms/individuals, merging surface variants."""

    def __init__(self, cert: Certificate):
        self.cert = cert
        self.preds: list[tuple[tuple[str, ...], str]] = []
        self.atoms: list[tuple[tuple[str, ...], str]] = []
        self.inds: dict[str, str] = {}
        self.ords: dict[str, str] = {}

    def pred(self, key: tuple[str, ...], surface: str) -> str:
        for k, sym in self.preds:
            if k == key:
                self._ident(sym, surface)
                return sym
        sym = "ABCDEFGH"[len(self.preds)]
        self.preds.append((key, sym))
        self._ident(sym, surface)
        return sym

    def atom(self, key: tuple[str, ...], surface: str) -> str:
        for k, sym in self.atoms:
            if (
                k == key
                or (len(k) > len(key) and k[-len(key) :] == key)
                or (len(key) > len(k) and key[-len(k) :] == k)
            ):
                self._ident(sym, surface)
                return sym
        sym = "PQRSTUVW"[len(self.atoms)]
        self.atoms.append((key, sym))
        self._ident(sym, surface)
        return sym

    def ind(self, name: str) -> str:
        if name not in self.inds:
            self.inds[name] = f"c{len(self.inds)}"
            self._ident(self.inds[name], name)
        return self.inds[name]

    def ord(self, name: str) -> str:
        if name not in self.ords:
            self.ords[name] = f"v{len(self.ords)}"
            self._ident(self.ords[name], name)
        return self.ords[name]

    def _ident(self, sym: str, surface: str) -> None:
        lst = self.cert.idents.setdefault(sym, [])
        if surface not in lst:
            lst.append(surface)


def _render(c: Clause, S: _Symbols) -> str:
    def tv(neg: bool) -> str:
        return "false" if neg else "true"

    if c.kind in {"all", "some", "none"}:
        subj, pred = c.args
        a = S.pred(subj, _surf(c, 0))
        b = S.pred(pred, _surf(c, 1))
        if c.kind == "all":
            return f"(∀ x, {a} x = true → {b} x = {tv(c.neg)})"
        if c.kind == "some":
            return f"(∃ x, {a} x = true ∧ {b} x = {tv(c.neg)})"
        return f"(∀ x, {a} x = true → {b} x = false)"
    if c.kind == "ind":
        name, pred = c.args
        return f"{S.pred(pred, _surf(c, 1))} {S.ind(name)} = {tv(c.neg)}"
    if c.kind == "prop":
        (a,) = c.args
        return f"{S.atom(a, c.src)} = {tv(c.neg)}"
    if c.kind == "if":
        (n1, a1), (n2, a2) = c.args
        return f"({S.atom(a1, _surf(c, 0))} = {tv(n1)} → {S.atom(a2, _surf(c, 1))} = {tv(n2)})"
    if c.kind == "or":
        (n1, a1), (n2, a2) = c.args
        return f"({S.atom(a1, _surf(c, 0))} = {tv(n1)} ∨ {S.atom(a2, _surf(c, 1))} = {tv(n2)})"
    if c.kind == "cmp":
        _fam, x, y = c.args
        return f"{S.ord(x)} > {S.ord(y)}"
    raise ValueError(c.kind)


def _surf(c: Clause, part: int) -> str:
    """Human-readable surface for the certificate: the clause split at its head."""
    ws = c.src.split()

    def clean(xs: list[str]) -> str:
        return " ".join(w for w in xs if w not in _NEG and w not in _COPULA and w != "يكن")

    if c.kind in {"all", "some", "none"}:
        start = 3 if c.kind == "none" else 1
        sp = _split_subject(ws[start:])
        if sp:
            return clean(sp[part])
    if c.kind == "ind":
        return clean(ws[1:])
    if c.kind == "if":
        idx = next((i for i, w in enumerate(ws) if w.startswith(_THEN)), len(ws))
        return " ".join(ws[1:idx] if part == 0 else ws[idx + 1 :])
    if c.kind == "or":
        body = ws[1:]
        j = body.index("أو") if "أو" in body else len(body)
        return " ".join(body[:j] if part == 0 else body[j + 1 :])
    return c.src


def _arith_content(c: Clause) -> bool:
    """Propositional atoms whose content is arithmetic («العدد 18 زوجي», «أ × ب يساوي 30»)
    are not propositional variables; leave them to the arithmetic fragment / the LLM."""
    if c.kind not in {"prop", "if", "or", "ind"}:
        return False
    keys = (
        [c.args[0]]
        if c.kind == "prop"
        else [c.args[0][1], c.args[1][1]]
        if c.kind != "ind"
        else [c.args[1]]
    )
    flat = [w for k in keys for w in k]
    if c.kind == "ind" and c.args[0].isdigit():
        flat.append(c.args[0])
    return any(
        re.fullmatch(r"-?\d+(\.\d+)?", w) or w in {"×", "+", "−", "-", "÷", "=", "يساوي"}
        for w in flat
    )


def formalize_logic_problem(problem: str) -> tuple[str, str] | None:
    """«premises. هل يلزم أن conclusion؟» -> universally closed `premises → conclusion` over a
    finite Bool model, plus a certificate. None if any sentence is outside the fragment."""
    split = _split_sentences(problem)
    if not split:
        return None
    sents, question = split
    clauses = [parse_clause(s) for s in sents]
    concl = parse_clause(question)
    if concl is None or any(c is None for c in clauses):
        return None
    fams = {c.args[0] for c in [*clauses, concl] if c and c.kind == "cmp"}
    if len(fams) > 1:
        return None
    if any(_arith_content(c) for c in [*clauses, concl] if c):
        return None
    cert = Certificate()
    S = _Symbols(cert)
    prem = [_render(c, S) for c in clauses if c]
    before = {s for _, s in S.preds} | {s for _, s in S.atoms}
    goal = _render(concl, S)
    if ({s for _, s in S.preds} | {s for _, s in S.atoms}) - before:
        return None  # the conclusion mentions a predicate no premise talks about: a lemma
        # identification was missed (or the question is outside the fragment) — do not
        # manufacture a "No" out of a translation gap
    for c in [*clauses, concl]:
        if c:
            cert.schemas.append(f"{c.kind}⟦{c.src}⟧")
    n = max(3, len(S.inds) + 1)
    binders = []
    if S.preds:
        binders.append(f"({' '.join(s for _, s in S.preds)} : Fin {n} → Bool)")
    if S.inds:
        binders.append(f"({' '.join(S.inds.values())} : Fin {n})")
    if S.atoms:
        binders.append(f"({' '.join(s for _, s in S.atoms)} : Bool)")
    if S.ords:
        binders.append(f"({' '.join(S.ords.values())} : Fin {len(S.ords) + 1})")
    if not binders:
        return None
    body = " → ".join([*prem, goal])
    prop = f"∀ {' '.join(binders)}, {body}"
    cert.schemas.insert(0, f"finite model Fin {n}")
    return prop, cert.render()
