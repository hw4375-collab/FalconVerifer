"""Generate bench/problems_daily_ar.jsonl: everyday Arabic dialogue turns, not textbook maths.

Each item is a short customer-service / shopping / booking / travel / family / scheduling
exchange rendered as dialogue text, followed by the question the assistant must answer.
Every item carries a `label`:

  inference  — the answer follows from the numbers/dates stated in the dialogue (checkable);
               `det` marks the sub-family the deterministic everyday fragment targets
               (weekday, clock, currency, unit, bill); the rest (kinship, scheduling
               conflict, cross-turn contradiction, conditional promise) go through the
               LLM formalizer and measure the *gap*.
  fact       — the answer is world knowledge (geography, calendar, prices) that Lean must
               NOT try to verify or refute (expected verdict: unverified_premise / skipped).
  chat       — small talk with no checkable claim (expected: skipped).

Run:  python bench/make_dataset_daily_ar.py
Then: falconverifier bench --dataset bench/problems_daily_ar.jsonl --tag inference ...
      python bench/daily_coverage.py           (deterministic coverage + fail-closed check)
"""

from __future__ import annotations

import json
import random
from pathlib import Path

rng = random.Random(9_2026_0925)
OUT = Path(__file__).parent / "problems_daily_ar.jsonl"

_EAST = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")
DAYS = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"]
NAMES = ["أحمد", "عمر", "خالد", "سعيد", "راشد", "فاطمة", "نور", "مريم", "هند", "سارة"]


def ar(n: int | float, eastern: bool) -> str:
    s = f"{n:g}"
    return s.translate(_EAST).replace(".", "٫") if eastern else s


def hhmm(m: int, eastern: bool) -> str:
    m %= 24 * 60
    return (
        ar(m // 60, eastern)
        + ":"
        + (f"{m % 60:02d}".translate(_EAST) if eastern else f"{m % 60:02d}")
    )


def dur(h: int, mins: int) -> str:
    hw = {0: "", 1: "ساعة", 2: "ساعتين"}.get(h, f"{h} ساعات")
    mw = {0: "", 30: "نصف", 15: "ربع", 45: "ثلاثة أرباع"}.get(mins, f"{mins} دقيقة")
    if h and mins:
        return f"{hw} و{mw}"
    return hw or mw


items: list[dict] = []


def add(scenario: str, label: str, det: str | None, dialogue: str, answer: str | None, **extra):
    tags = ["daily", "ar", scenario, label] + ([f"det:{det}"] if det else [])
    items.append(
        {
            "id": f"daily-{len(items) + 1:03d}",
            "scenario": scenario,
            "label": label,
            "det": det,
            "problem": dialogue,
            "answer": answer,
            "tags": tags,
            **extra,
        }
    )


# --- inference, deterministic-target ----------------------------------------------------

for _ in range(12):  # weekday
    e = rng.random() < 0.5
    today = rng.randrange(7)
    k = rng.choice([3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14])
    back = rng.random() < 0.3
    ans = DAYS[(today - k) % 7] if back else DAYS[(today + k) % 7]
    ctx = rng.choice(["موعد الطبيب", "تسليم الطلب", "الرحلة", "الامتحان", "زيارة العائلة"])
    q = f"ما اليوم قبل {ar(k, e)} أيام؟" if back else f"ما اليوم بعد {ar(k, e)} أيام؟"
    add(
        "scheduling",
        "inference",
        "weekday",
        f"العميل: اليوم {DAYS[today]}، و{ctx} {'كان قبل' if back else 'بعد'} {ar(k, e)} أيام. {q}",
        ans,
    )

for _ in range(12):  # clock
    e = rng.random() < 0.5
    start = rng.choice([8 * 60, 9 * 60, 9 * 60 + 30, 10 * 60 + 15, 13 * 60, 14 * 60 + 20, 20 * 60])
    h, mins = rng.choice([(1, 0), (1, 30), (2, 0), (2, 45), (3, 50), (0, 45), (1, 15)])
    ev = rng.choice(["الاجتماع", "الفيلم", "المحاضرة", "الرحلة", "الموعد"])
    add(
        "scheduling",
        "inference",
        "clock",
        f"العميل: بدأ {ev} في الساعة {hhmm(start, e)} واستمر {dur(h, mins)}. في أي ساعة انتهى؟",
        hhmm(start + h * 60 + mins, False),
    )

for _ in range(12):  # currency
    e = rng.random() < 0.5
    cur, rate = rng.choice([("درهم", 3.67), ("ريال", 3.75), ("دينار", 0.31), ("جنيه", 48.5)])
    amt = rng.choice([50, 100, 150, 200, 250, 400, 500, 800])
    if rng.random() < 0.4:  # foreign → local
        add(
            "travel",
            "inference",
            "currency",
            f"العميل: ١ دولار = {ar(rate, e)} {cur}. كم {cur}اً يساوي {ar(amt, e)} دولاراً؟",
            f"{amt * rate:g}",
        )
    else:
        n = rng.choice([2, 3, 5, 10, 20])
        add(
            "travel",
            "inference",
            "currency",
            f"العميل: ١ دولار = {ar(rate, e)} {cur}. كم دولاراً يساوي {ar(n * rate, e)} {cur}اً؟",
            f"{n}",
        )

for _ in range(10):  # units
    e = rng.random() < 0.5
    fam = rng.choice(
        [
            ("كيلومتر", "متراً", 1000),
            ("ساعات", "دقيقة", 60),
            ("كيلوغرام", "غراماً", 1000),
            ("لتر", "مليلتر", 1000),
            ("أيام", "ساعة", 24),
        ]
    )
    n = rng.choice([2, 3, 3.5, 4, 5, 7.5, 12])
    add(
        "shopping",
        "inference",
        "unit",
        f"العميل: كم {fam[1]} في {ar(n, e)} {fam[0]}؟",
        f"{n * fam[2]:g}",
    )

for _ in range(18):  # bills
    e = rng.random() < 0.5
    base = rng.choice([80, 120, 150, 200, 240, 300, 450, 600])
    total = float(base)
    parts = [f"الفاتورة {ar(base, e)} درهماً"]
    shape = rng.choice(
        ["tax_service_split", "discount_tip", "tax_split", "discount", "service_tip_split"]
    )
    if "tax" in shape:
        t = rng.choice([5, 10])
        total *= 1 + t / 100
        parts.append(f"تضاف ضريبة {ar(t, e)}٪")
    if "service" in shape:
        s = rng.choice([10, 12, 15])
        total *= 1 + s / 100
        parts.append(f"رسوم خدمة {ar(s, e)}٪")
    if "discount" in shape:
        d = rng.choice([10, 20, 25])
        total *= 1 - d / 100
        parts.append(f"مع خصم {ar(d, e)}٪")
    if "tip" in shape:
        tip = rng.choice([10, 15, 20])
        total += tip
        parts.append(f"أضاف بقشيشاً {ar(tip, e)} دراهم")
    if "split" in shape:
        k = rng.choice([2, 3, 4, 5])
        total /= k
        parts.append(f"تقاسمها {ar(k, e)} أشخاص بالتساوي")
        q = "كم يدفع كل واحد؟"
    else:
        q = "كم دفع في النهاية؟"
    add(
        "restaurant",
        "inference",
        "bill",
        "العميل: " + "، و".join(parts) + f". {q}",
        f"{round(total, 2):g}",
    )

# --- inference, beyond the deterministic fragment (LLM formalizer path) ------------------

KIN = [
    ("ابن أخي", "ابن أخي، ما علاقته بأبي؟", "حفيده"),
    ("أخو أمي", "أخو أمي، ما علاقته بي؟", "خالي"),
    ("أخو أبي", "أخو أبي، ما علاقته بي؟", "عمي"),
    ("ابن عمي", "أبو ابن عمي، ما علاقته بأبي؟", "أخوه"),
    ("أم أبي", "أم أبي، ما علاقتها بي؟", "جدتي"),
    ("بنت أختي", "بنت أختي، ما علاقتي بها؟", "خالها"),
]
for _, q, a in KIN:
    add("family", "inference", None, f"العميل: {q}", a, family="kinship")

for _ in range(8):  # scheduling conflict
    e = rng.random() < 0.5
    a0 = rng.choice([9 * 60, 10 * 60, 13 * 60, 15 * 60])
    a1 = a0 + rng.choice([60, 90])
    gap = rng.choice([-30, 0, 30, 60])
    b0 = a1 + gap
    b1 = b0 + 60
    overlap = b0 < a1
    add(
        "scheduling",
        "inference",
        None,
        f"العميل: لدي اجتماع من {hhmm(a0, e)} إلى {hhmm(a1, e)}، وموعد آخر من {hhmm(b0, e)} إلى {hhmm(b1, e)}. هل يتعارض الموعدان؟ أجب بنعم أو لا.",
        "نعم" if overlap else "لا",
        family="conflict",
    )

for _ in range(8):  # cross-turn contradiction
    e = rng.random() < 0.5
    n1 = rng.choice([3, 4, 5, 6])
    same = rng.random() < 0.5
    n2 = n1 if same else n1 + rng.choice([1, 2])
    name = rng.choice(NAMES)
    add(
        "customer_service",
        "inference",
        None,
        f"العميل: طلبت {ar(n1, e)} قطع من المنتج.\nالمساعد: حسناً.\nالعميل: أريد استرجاع كل القطع، وعددها {ar(n2, e)}.\nالسؤال: هل كلام العميل متسق بين الرسالتين؟ أجب بنعم أو لا.",
        "نعم" if same else "لا",
        family="contradiction",
        speaker=name,
    )

for _ in range(8):  # conditional promise
    e = rng.random() < 0.5
    thr = rng.choice([200, 300, 500])
    amt = thr + rng.choice([-50, -1, 0, 1, 80])
    add(
        "shopping",
        "inference",
        None,
        f"المتجر: الشحن مجاني إذا تجاوز الطلب {ar(thr, e)} درهماً.\nالعميل: طلبي {ar(amt, e)} درهماً. هل الشحن مجاني؟ أجب بنعم أو لا.",
        "نعم" if amt > thr else "لا",
        family="conditional",
    )

# --- fact: world knowledge, must not be refuted by Lean ------------------------------------

FACTS = [
    ("travel", "العميل: في أي دولة تقع مكة المكرمة؟", "السعودية"),
    ("travel", "العميل: ما عاصمة الإمارات؟", "أبوظبي"),
    ("travel", "العميل: ما العملة الرسمية في الكويت؟", "الدينار"),
    ("travel", "العميل: هل تحتاج تأشيرة للسفر من الإمارات إلى عُمان بجواز إماراتي؟", None),
    ("customer_service", "العميل: كم يوماً في شهر رمضان؟", "29 أو 30"),
    ("customer_service", "العميل: ما رقم الطوارئ في الإمارات؟", "999"),
    ("shopping", "العميل: كم سعر آيفون الجديد اليوم؟", None),
    ("shopping", "العميل: هل الحليب كامل الدسم أغلى من الخالي من الدسم عادة؟", None),
    ("family", "العميل: في أي عيد يذبح المسلمون الأضاحي؟", "عيد الأضحى"),
    ("scheduling", "العميل: هل الجمعة يوم عطلة رسمية في السعودية؟", "نعم"),
    ("travel", "العميل: كم تبعد دبي عن أبوظبي بالكيلومتر تقريباً؟", None),
    ("customer_service", "العميل: هل يعمل البنك المركزي يوم السبت؟", None),
]
for sc, q, a in FACTS:
    add(sc, "fact", None, q, a, expected_verdicts=["unverified_premise", "skipped", "unknown"])

# --- chat: no checkable claim ------------------------------------------------------------

CHAT = [
    ("customer_service", "العميل: السلام عليكم، كيف حالك اليوم؟"),
    ("customer_service", "العميل: شكراً جزيلاً على مساعدتك!"),
    ("shopping", "العميل: أحب اللون الأزرق أكثر من الأحمر، ما رأيك؟"),
    ("family", "العميل: أمي طبخت اليوم مجبوساً لذيذاً."),
    ("travel", "العميل: أتمنى أن يكون الطقس جميلاً في الرحلة."),
    ("scheduling", "العميل: أشعر بالتوتر قبل الاجتماع غداً."),
    ("customer_service", "العميل: هل يمكنك أن تتكلم معي بلهجة خليجية؟"),
    ("shopping", "العميل: القهوة العربية أفضل من الإسبريسو في رأيي."),
    ("travel", "العميل: ما أجمل مدينة زرتها؟"),
    ("family", "العميل: ابني الصغير قال أول كلمة اليوم!"),
]
for sc, q in CHAT:
    add(sc, "chat", None, q, None, expected_verdicts=["skipped"])

OUT.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in items) + "\n")
by = {}
for x in items:
    by[x["label"]] = by.get(x["label"], 0) + 1
print(f"wrote {len(items)} items to {OUT.name}: {by}")
