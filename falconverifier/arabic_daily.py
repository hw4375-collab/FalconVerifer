"""Deterministic fragment for *everyday* Arabic reasoning: weekdays, clock times, currency
and unit conversion, bills with tax / service / tip / split.

These are the small calculations that actually occur in Arabic assistant conversations
(booking, shopping, travel, scheduling) — not textbook mathematics.  As in `arabic_word`,
a question is a sequence of clauses folded into one running Lean expression; every clause
must be recognised or the fragment returns None (the LLM formalizer then takes over).

    اليوم الثلاثاء. ما اليوم بعد ١٠ أيام؟                 ((2:ℕ) + 10) % 7 = 5   (الجمعة)
    بدأ الاجتماع ٩:٣٠ واستمر ساعتين و٤٥ دقيقة. متى انتهى؟   9*60+30 + (2*60+45) = 12*60+15
    ١ دولار = ٣٫٦٧ درهم. كم درهماً في ٢٥٠ دولاراً؟           (250:ℚ) * 3.67 = 917.5
    الفاتورة ٢٤٠ درهماً، ضريبة ٥٪ وخدمة ١٠٪، تقاسمها ٣.     (240:ℚ) * (1+5/100) * (1+10/100) / 3 = 92.4

The certificate lists the clauses that fired, so the translation is mechanical and auditable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .arabic import normalize_digits
from .arabic_word import _DIACRITICS, _NUM, _clean, _par

_DAYS = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
_DAY_ALT = {"الإثنين": "الاثنين", "الأثنين": "الاثنين"}
_DAY_RE = "|".join(_DAYS + list(_DAY_ALT))

_COUNT_WORDS = {
    "ساعة": 1,
    "ساعتين": 2,
    "ساعتان": 2,
    "ثلاث": 3,
    "أربع": 4,
    "خمس": 5,
    "ست": 6,
    "سبع": 7,
    "ثماني": 8,
    "تسع": 9,
    "عشر": 10,
    "دقيقة": 1,
    "دقيقتين": 2,
    "دقيقتان": 2,
    "يوم": 1,
    "يومين": 2,
    "يومان": 2,
    "أسبوع": 7,
    "أسبوعين": 14,
    "أسبوعان": 14,
}

# unit → (base unit, factor): 1 unit = factor base
_UNITS: dict[str, tuple[str, str]] = {
    "كيلومتر": ("متر", "1000"),
    "كيلومترا": ("متر", "1000"),
    "كم": ("متر", "1000"),
    "كيلوغرام": ("غرام", "1000"),
    "كيلوغراما": ("غرام", "1000"),
    "كيلوجرام": ("غرام", "1000"),
    "كغ": ("غرام", "1000"),
    "لتر": ("مل", "1000"),
    "لترا": ("مل", "1000"),
    "ساعة": ("دقيقة", "60"),
    "ساعات": ("دقيقة", "60"),
    "دقيقة": ("ثانية", "60"),
    "دقائق": ("ثانية", "60"),
    "يوم": ("ساعة", "24"),
    "أيام": ("ساعة", "24"),
    "أسبوع": ("يوم", "7"),
    "أسابيع": ("يوم", "7"),
    "سنة": ("شهر", "12"),
    "متر": ("سم", "100"),
    "مترا": ("سم", "100"),
}
_UNIT_NORM = {"أمتار": "متر", "متر": "متر", "غرامات": "غرام", "سم": "سم", "مل": "مل"}
_CUR = r"(?:درهما?|دراهم|دولارا?|دولارات|ريالا?|ريالات|يورو|جنيها?|جنيهات|دينارا?|دنانير|ليرة)"
_CUR_KEY = {
    "درهم": "درهم",
    "دولار": "دولار",
    "ريال": "ريال",
    "يورو": "يورو",
    "جنيه": "جنيه",
    "دينار": "دينار",
    "ليرة": "ليرة",
}


def _cur(w: str) -> str:
    for k in _CUR_KEY:
        if w.startswith(k):
            return k
    return w


def _day_index(w: str) -> int | None:
    w = _DAY_ALT.get(w, w)
    return _DAYS.index(w) if w in _DAYS else None


def _count(tok: str) -> int | None:
    tok = normalize_digits(tok)
    if tok.isdigit():
        return int(tok)
    return _COUNT_WORDS.get(tok)


@dataclass(frozen=True)
class Daily:
    kind: str  # weekday | clock | convert | bill
    expr: str  # Lean expression for the asked quantity
    fired: list[str]

    def prop(self, answer: str) -> str | None:
        a = _clean(answer)
        if self.kind == "weekday":
            m = re.search(_DAY_RE, a)
            if not m:
                return None
            return f"{self.expr} = {_day_index(m.group(0))}"
        if self.kind == "clock":
            m = re.search(r"(\d{1,2})[:٫.](\d{2})", a)
            if not m:
                return None
            h, mi = int(m.group(1)), int(m.group(2))
            if "مساء" in a or "ظهر" in a and h < 12:
                h = h + 12 if h < 12 else h
            return f"{self.expr} = {h} * 60 + {mi}"
        m = re.search(r"-?\d+(?:\.\d+)?", a.replace(",", ""))
        if not m:
            return None
        ans = m.group(0)
        if "." in ans:
            tol = f"(1 / 10 ^ {len(ans.split('.')[1])} : ℚ)"
            return f"{self.expr} - {ans} < {tol} ∧ {ans} - {_par(self.expr)} < {tol}"
        return f"{self.expr} = {ans}"

    def certificate(self) -> str:
        return f"{self.kind}: " + " → ".join(self.fired) + f" ⇒ {self.expr}"


def _split(text: str) -> list[str]:
    parts = re.split(
        r"،|(?<!\d)\.|\.(?!\d)|[؛؟?!]|\s+ثم\s+"
        r"|\s+و(?=استمر|تستمر|يستمر|أضاف|أُضيف|تُضاف|تضاف|يضاف|تقاسم|قسم|رسوم|خدمة|ضريبة|خصم|بقشيش|مع\s)",
        text,
    )
    out = []
    for p in parts:
        p = p.strip(" ،.")
        p = _LEAD_WAW.sub("", p)
        if p:
            out.append(p)
    return out


# dialogue rendering: «العميل: …» / «المساعد: …» speaker labels carry no content
_SPEAKER = re.compile(
    r"(?:^|(?<=[\n.؟!]))\s*(?:العميل|المساعد|المتجر|السؤال|الموظف|الزبون|المستخدم)\s*:\s*"
)
# a clause-initial «و» before a known clause opener is the conjunction, not part of the word
_LEAD_WAW = re.compile(
    r"^و(?=ال|تضاف|تُضاف|يضاف|أضاف|رسوم|خدمة|ضريبة|خصم|بقشيش|مع\s|تقاسم|قسم|استمر|تستمر|يستمر|زيارة|تسليم|موعد)"
)


# ── weekdays ───────────────────────────────────────────────────────────────────
_TODAY = re.compile(
    rf"^(?:اليوم|نحن\s+اليوم\s+في|إذا\s+كان\s+اليوم)\s+(?:هو\s+)?(?:يوم\s+)?({_DAY_RE})$"
)
_AFTER_DAYS = re.compile(
    r"^(?:ما|ماذا|أي)\s+(?:هو\s+)?(?:اليوم|يوم)\s+(?:سيكون\s+)?(بعد|قبل)\s+(\S+)\s*(أيام|يوما|يوم|أسابيع|أسبوعا|أسبوع)?$"
)


_EVENT_DAYS = re.compile(
    r"^\S+(?:\s+\S+)?\s+(?:كان\s+|سيكون\s+)?(بعد|قبل)\s+(\S+)\s*(أيام|يوما|يوم|أسابيع|أسبوعا|أسبوع)?$"
)


def _weekday(clauses: list[str]) -> Daily | None:
    fired = ["today"]
    if len(clauses) == 3:
        ev = _EVENT_DAYS.match(clauses[1])
        q = _AFTER_DAYS.match(clauses[2])
        if not (
            ev and q and ev.group(1) == q.group(1) and _count(ev.group(2)) == _count(q.group(2))
        ):
            return None
        fired.append("event restated")
        clauses = [clauses[0], clauses[2]]
    if len(clauses) != 2:
        return None
    m1, m2 = _TODAY.match(clauses[0]), _AFTER_DAYS.match(clauses[1])
    if not (m1 and m2):
        return None
    idx = _day_index(m1.group(1))
    n = _count(m2.group(2))
    if idx is None or n is None:
        return None
    unit = m2.group(3) or ""
    if unit.startswith("أسب") or m2.group(2) in ("أسبوع", "أسبوعين", "أسبوعان"):
        if not m2.group(2).startswith("أسب"):
            n *= 7
    if m2.group(1) == "بعد":
        expr = f"(({idx}:ℕ) + {n}) % 7"
    else:
        expr = f"(({idx}:ℕ) + {7 * (n // 7 + 1)} - {n}) % 7"
    return Daily("weekday", expr, fired + [f"{m2.group(1)} {n} days"])


# ── clock times ────────────────────────────────────────────────────────────────
_START = re.compile(
    r"^(?:بدأ|بدأت|يبدأ|تبدأ|انطلق|انطلقت|تنطلق)\s+\S+\s+(?:في\s+)?(?:الساعة\s+)?(\d{1,2})[:٫.](\d{2})(?:\s+(صباحا|مساء|ظهرا))?$"
)
_LASTS = re.compile(r"^(?:و?استمر|و?استمرت|و?يستمر|و?تستمر|لمدة|مدته|مدتها|و?تأخر|و?تأخرت)\s+(.+)$")
_DUR_PART = re.compile(r"(\S+)\s*(ساعات|ساعة|ساعتين|ساعتان|دقائق|دقيقة|دقيقتين|دقيقتان)?")
_ASK_END = re.compile(r"^(?:في\s+أي\s+ساعة|متى|ما\s+(?:هو\s+)?(?:وقت|موعد))\s+.*$")


def _duration_minutes(text: str) -> int | None:
    text = normalize_digits(text).replace("ونصف", "و 30 دقيقة").replace("وربع", "و 15 دقيقة")
    text = text.replace("نصف ساعة", "30 دقيقة").replace("ربع ساعة", "15 دقيقة")
    text = re.sub(r"ثلاثة\s+أرباع(?:\s+(?:ال)?ساعة)?", "45 دقيقة", text).replace("نصف", "30 دقيقة")
    total = 0
    found = False
    for part in re.split(r"\s+و\s*|\s+و(?=\d)", text):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*(ساعات|ساعة|دقائق|دقيقة)", part)
        if m:
            n, unit = int(m.group(1)), m.group(2)
        elif part in ("ساعة", "ساعتين", "ساعتان"):
            n, unit = _COUNT_WORDS[part], "ساعة"
        elif part in ("دقيقة", "دقيقتين", "دقيقتان"):
            n, unit = _COUNT_WORDS[part], "دقيقة"
        else:
            m = re.fullmatch(r"(\S+)\s+(ساعات|دقائق)", part)
            if not m or _count(m.group(1)) is None:
                return None
            n, unit = _count(m.group(1)) or 0, m.group(2)
        total += n * 60 if unit.startswith("ساع") else n
        found = True
    return total if found else None


def _clock(clauses: list[str]) -> Daily | None:
    if len(clauses) != 3:
        return None
    m1, m2 = _START.match(clauses[0]), _LASTS.match(clauses[1])
    if not (m1 and m2 and _ASK_END.match(clauses[2])):
        return None
    h, mi = int(m1.group(1)), int(m1.group(2))
    if m1.group(3) == "مساء" and h < 12:
        h += 12
    dur = _duration_minutes(m2.group(1))
    if dur is None:
        return None
    expr = f"(({h}:ℕ) * 60 + {mi} + {dur})"
    return Daily("clock", expr, [f"start {h}:{mi:02d}", f"lasts {dur} min"])


# ── currency / unit conversion ─────────────────────────────────────────────────
_RATE = re.compile(
    rf"^(?:إذا\s+كان\s+)?(?:1|١)?\s*({_CUR})\s*(?:=|يساوي|يعادل)\s*{_NUM}\s*({_CUR})$"
)
_ASK_CUR = re.compile(
    rf"^(?:كم|ما\s+(?:هو\s+)?(?:قيمة|مقابل))\s+({_CUR})\s+(?:يساوي|تساوي|يعادل|تعادل|في|مقابل|هي\s+قيمة)\s+{_NUM}\s*({_CUR})$"
)
_ASK_UNIT = re.compile(rf"^كم\s+(\S+)\s+(?:في|يساوي|تساوي|يعادل|تعادل|هناك\s+في)\s+{_NUM}\s*(\S+)$")


def _convert(clauses: list[str]) -> Daily | None:
    if len(clauses) == 1:
        m = _ASK_UNIT.match(clauses[0])
        if not m:
            return None
        target, n, src = _UNIT_NORM.get(m.group(1), m.group(1).rstrip("ا")), m.group(2), m.group(3)
        if src in _UNITS and _UNITS[src][0] == target:
            base, f = _UNITS[src]
            return Daily("convert", f"({n}:ℚ) * {f}", [f"1 {src} = {f} {base}"])
        for u, (base, f) in _UNITS.items():
            if base == src.rstrip("ا") and _UNIT_NORM.get(target, target) == u:
                return Daily("convert", f"({n}:ℚ) / {f}", [f"1 {u} = {f} {base}"])
        return None
    if len(clauses) != 2:
        return None
    m1, m2 = _RATE.match(clauses[0]), _ASK_CUR.match(clauses[1])
    if not (m1 and m2):
        return None
    one, rate, other = _cur(m1.group(1)), m1.group(2), _cur(m1.group(3))
    want, n, have = _cur(m2.group(1)), m2.group(2), _cur(m2.group(3))
    if (want, have) == (other, one):
        return Daily("convert", f"({n}:ℚ) * {rate}", [f"1 {one} = {rate} {other}"])
    if (want, have) == (one, other):
        return Daily("convert", f"({n}:ℚ) / {rate}", [f"1 {one} = {rate} {other}"])
    return None


# ── bills ──────────────────────────────────────────────────────────────────────
_BILL = re.compile(
    rf"^(?:بلغت|كانت|قيمة|مجموع)?\s*(?:الفاتورة|فاتورة\s+\S+|الحساب)\s+(?:هي\s+)?{_NUM}\s*{_CUR}?$"
)
_ADD_PCT = re.compile(
    rf"^(?:و?تُضاف|و?تضاف|و?يضاف|و?أُضيفت|و?أضيفت|و?أُضيف|و?أضيف|و?مع|و?عليها|و?زائد|و?بالإضافة\s+إلى)?\s*(?:ضريبة|ضريبة\s+القيمة\s+المضافة|رسوم\s+خدمة|رسوم|خدمة|رسم\s+خدمة)\s*(?:بنسبة\s+|قدرها\s+)?{_NUM}\s*%$"
)
_TIP = re.compile(
    rf"^(?:و?أضاف|و?أضافت|و?ترك|و?تركت|و?مع)\s+(?:بقشيشا|إكرامية|بقشيش)\s+(?:قدره\s+|قدرها\s+)?{_NUM}\s*{_CUR}?$"
)
_DISCOUNT = re.compile(
    rf"^(?:و?مع|و?بعد|و?خُصم|و?خصم|و?خُفِّضت|و?خفضت)\s+(?:خصم|خصما|بنسبة|تخفيض)?\s*(?:بنسبة\s+|قدره\s+)?{_NUM}\s*%$"
)
_SPLIT = re.compile(
    r"^(?:و?تقاسمها|و?تقاسموها|و?قسموها|و?قُسمت|و?قسمت|و?يتقاسمها)\s+(?:بالتساوي\s+)?(?:بين\s+|على\s+)?(\S+)\s*(?:أشخاص|أصدقاء|شخصا|أفراد)?\s*(?:بالتساوي)?$"
)
_ASK_BILL = re.compile(
    r"^(?:ما|كم)\s+.*(?:المجموع|الإجمالي|النهائي|يدفع|تدفع|المبلغ|الفاتورة).*$|^كم\s+(?:يدفع|تدفع|دفع)\b.*$"
)


def _bill(clauses: list[str]) -> Daily | None:
    if len(clauses) < 2 or not _ASK_BILL.match(clauses[-1]):
        return None
    m = _BILL.match(clauses[0])
    if not m:
        return None
    expr = f"({m.group(1)}:ℚ)"
    fired = ["bill"]
    split_asked = bool(re.search(r"كل\s+(?:واحد|شخص|فرد)", clauses[-1]))
    split_seen = False
    for cl in clauses[1:-1]:
        if mm := _ADD_PCT.match(cl):
            expr += f" * (1 + {mm.group(1)} / 100)"
            fired.append(f"+{mm.group(1)}%")
        elif mm := _DISCOUNT.match(cl):
            expr += f" * (1 - {mm.group(1)} / 100)"
            fired.append(f"-{mm.group(1)}%")
        elif mm := _TIP.match(cl):
            expr = f"({expr} + {mm.group(1)})"
            fired.append(f"tip {mm.group(1)}")
        elif mm := _SPLIT.match(cl):
            n = _count(mm.group(1))
            if n is None:
                return None
            expr = f"{expr} / {n}"
            fired.append(f"split {n}")
            split_seen = True
        else:
            return None
    if split_asked and not split_seen:
        return None
    return Daily("bill", expr, fired)


def analyze(problem: str) -> Daily | None:
    text = _clean(_SPEAKER.sub(". ", _DIACRITICS.sub("", problem)).replace("\n", ". "))
    clauses = _split(text)
    if not clauses:
        return None
    for fn in (_weekday, _clock, _convert, _bill):
        d = fn(clauses)
        if d is not None:
            return d
    return None


def formalize_daily(problem: str, final_answer: str | None) -> tuple[str, str] | None:
    """Lean proposition + clause certificate for an everyday question, or None."""
    if final_answer is None:
        return None
    d = analyze(problem)
    if d is None:
        return None
    prop = d.prop(final_answer)
    if prop is None:
        return None
    return prop, d.certificate()
