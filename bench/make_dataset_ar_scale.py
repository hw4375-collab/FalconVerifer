"""Generate bench/problems_ar_scale.jsonl: a large Arabic set for DPO data collection.

Not a benchmark: it reuses the template families of make_dataset_ar.py (arithmetic, percent,
compound percent, order of operations, quantifier syllogisms, transitivity, relation/counting)
with a different seed and many more instances, so closed-loop runs produce Lean-backed
preference pairs at scale (see docs/DPO.md). Run:  python bench/make_dataset_ar_scale.py [N]
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

rng = random.Random(3_2026_0925)
OUT = Path(__file__).parent / "problems_ar_scale.jsonl"

NAMES_M = ["أحمد", "عمر", "يوسف", "خالد", "حمدان", "زايد", "سلطان", "راشد", "سعيد", "ماجد"]
NAMES_F = ["عائشة", "ليلى", "فاطمة", "نور", "سارة", "مريم", "هند", "شمسة"]
ITEMS = ["كتاباً", "قلماً", "تمرة", "كوباً", "تذكرة", "زجاجة", "صندوقاً", "عملة", "كرسياً"]
PRODUCTS = ["هاتف", "حاسوب", "ساعة", "حقيبة", "دراجة", "معطف", "طاولة"]

_EAST = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# (plural noun, singular-ish predicate for «كل X Y»); every pair is a true-by-stipulation premise
CLASSES = [
    ("المربعات", "مستطيلات", "أشكال رباعية"),
    ("الأطباء", "متعلمون", "بشر"),
    ("القطط", "ثدييات", "حيوانات"),
    ("الخفافيش", "ثدييات", "كائنات حية"),
    ("المعلمين", "موظفون", "مواطنون"),
    ("الطلاب", "قراء", "متعلمون"),
    ("الورود", "نباتات", "كائنات حية"),
]
OTHERS = ["فقراء", "أغنياء", "سعداء", "طيور", "زواحف", "أطباء", "شعراء"]


def ar(n: int, eastern: bool) -> str:
    return str(n).translate(_EAST) if eastern else str(n)


def gen_math(n_per: int) -> list[dict]:
    out: list[dict] = []

    def add(problem: str, answer, tags: list[str], eastern: bool) -> None:
        out.append(
            {
                "problem": problem,
                "answer": str(answer),
                "tags": ["math", "arabic", *tags, *(["eastern-digits"] if eastern else [])],
            }
        )

    for i in range(n_per):
        e = i % 2 == 0
        a, b = rng.randint(13, 98), rng.randint(12, 49)
        add(f"ما هو ناتج {ar(a, e)} × {ar(b, e)}؟", a * b, ["arith", "fragment"], e)
    for i in range(n_per):
        e = i % 2 == 0
        a, b, c = rng.randint(120, 980), rng.randint(110, 490), rng.randint(20, 99)
        add(
            f"احسب مجموع {ar(a, e)} و {ar(b, e)} ناقص {ar(c, e)}.",
            a + b - c,
            ["arith", "fragment"],
            e,
        )
    for i in range(n_per):
        e = i % 2 == 0
        p = rng.choice([10, 20, 25, 40, 50, 75])
        base = rng.choice([80, 120, 160, 200, 240, 360, 480, 640])
        add(
            f"كم يساوي {ar(p, e)}٪ من {ar(base, e)}؟",
            base * p // 100,
            ["arith", "percent", "fragment"],
            e,
        )
    for i in range(n_per):
        e = i % 2 == 0
        a, b, c = rng.randint(23, 98), rng.randint(12, 49), rng.randint(50, 400)
        n, it = rng.choice(NAMES_M), rng.choice(ITEMS)
        add(
            f"اشترى {n} {ar(a, e)} علبة تحتوي كل منها على {ar(b, e)} {it}، ثم أعطى {ar(c, e)} {it} "
            f"من مجموعها لأصدقائه. كم {it} بقي لدى {n}؟",
            a * b - c,
            ["arith", "multiply"],
            e,
        )
    for i in range(n_per):
        e = i % 2 == 0
        price = rng.choice([80, 120, 150, 200, 240, 360, 400, 500, 600])
        pct = rng.choice([10, 15, 20, 25, 30, 40])
        add(
            f"يبلغ سعر {rng.choice(PRODUCTS)} {ar(price, e)} درهماً. خُفِّض سعره بنسبة {ar(pct, e)}٪. "
            f"ما هو السعر الجديد بالدرهم؟",
            price - price * pct // 100,
            ["arith", "percent"],
            e,
        )
    for i in range(n_per):
        e = i % 2 == 0
        k = rng.randint(4, 6)
        vals = [rng.randint(40, 99) for _ in range(k)]
        vals[-1] += (-sum(vals)) % k
        n = rng.choice(NAMES_F)
        add(
            f"حصلت {n} على الدرجات {'، '.join(ar(v, e) for v in vals)} في {ar(k, e)} اختبارات. "
            f"ما هو متوسط درجاتها؟",
            sum(vals) // k,
            ["arith", "average"],
            e,
        )
    for i in range(n_per):
        e = i % 2 == 0
        total, per = rng.randint(150, 900), rng.randint(7, 24)
        add(
            f"لدينا {ar(total, e)} تفاحة نضعها في صناديق تتسع كل منها {ar(per, e)} تفاحة. "
            f"كم صندوقاً ممتلئاً نحصل عليه؟",
            total // per,
            ["arith", "division"],
            e,
        )
    for i in range(n_per):
        e = i % 2 == 0
        n1, p1, n2, p2 = (
            rng.randint(3, 12),
            rng.randint(7, 45),
            rng.randint(2, 9),
            rng.randint(11, 60),
        )
        cost = n1 * p1 + n2 * p2
        paid = ((cost // 100) + 2) * 100
        n = rng.choice(NAMES_F)
        add(
            f"اشترت {n} {ar(n1, e)} دفاتر بسعر {ar(p1, e)} درهماً للدفتر و{ar(n2, e)} أقلام بسعر "
            f"{ar(p2, e)} درهماً للقلم، ودفعت {ar(paid, e)} درهماً. كم درهماً تستعيد؟",
            paid - cost,
            ["arith", "money"],
            e,
        )
    for i in range(n_per):
        e = i % 2 == 0
        price = rng.choice([800, 1200, 1500, 2400, 3000, 4000])
        p1, p2 = rng.choice([10, 20, 25, 50]), rng.choice([10, 20, 25])
        add(
            f"يبلغ سعر {rng.choice(PRODUCTS)} {ar(price, e)} درهماً. خُفِّض بنسبة {ar(p1, e)}٪ ثم خُفِّض "
            f"السعر الجديد بنسبة {ar(p2, e)}٪ أخرى. ما هو السعر النهائي بالدرهم؟",
            price * (100 - p1) * (100 - p2) // 10000,
            ["arith", "compound-percent", "hard"],
            e,
        )
    for i in range(n_per):
        e = i % 2 == 0
        a, b, c, d = rng.randint(10, 60), rng.randint(3, 12), rng.randint(3, 12), rng.randint(2, 9)
        add(
            f"احسب قيمة {ar(a, e)} + {ar(b, e)} × {ar(c, e)} − {ar(d, e)}² باتباع ترتيب العمليات.",
            a + b * c - d * d,
            ["arith", "order-of-operations", "hard"],
            e,
        )
    return out


def gen_logic(n_per: int) -> list[dict]:
    L: list[dict] = []

    def add(problem: str, answer: str, tags: list[str]) -> None:
        L.append(
            {
                "problem": problem + " أجب بنعم أو لا.",
                "answer": answer,
                "tags": ["logic", "arabic", *tags],
            }
        )

    for _ in range(n_per):
        a, b, c = rng.choice(CLASSES)
        add(f"كل {a} {b}، وكل ال{b} {c}. هل يلزم أن كل {a} {c}؟", "نعم", ["syllogism", "valid"])
        o = rng.choice(OTHERS)
        add(
            f"كل {a} {b}، وبعض ال{b} {o}. هل يلزم أن بعض {a} {o}؟",
            "لا",
            ["syllogism", "invalid", "undistributed-middle"],
        )
        add(
            f"لا شيء من {a} {o}، وكل ال{b} {o}. هل يلزم أن لا شيء من {a} {b}؟",
            "نعم",
            ["syllogism", "valid"],
        )
        add(
            f"كل {a} {b}، وبعض ال{b} ليست {a}. هل يلزم أن بعض {a} ليست {b}؟",
            "لا",
            ["syllogism", "invalid", "illicit-conversion"],
        )
    for _ in range(n_per):
        x, y, z = rng.sample(NAMES_M, 3)
        add(
            f"{x} أطول من {y}، و{y} أطول من {z}. هل يلزم أن {x} أطول من {z}؟",
            "نعم",
            ["relation", "transitivity"],
        )
        add(
            f"{x} أطول من {y}، و{x} أطول من {z}. هل يلزم أن {y} أطول من {z}؟",
            "لا",
            ["relation", "invalid"],
        )
    for i in range(n_per):
        e = i % 2 == 0
        n = rng.choice([5, 7, 9, 11])
        k = rng.choice([1, 3, 5])
        if k >= n:
            k = 1
        add(
            f"في غرفة {ar(n, e)} أشخاص، يقول كل واحد منهم إن {ar(k, e)} من الباقين أصدقاؤه. "
            f"هل يمكن أن يكون الجميع صادقين؟",
            "لا",
            ["relation", "handshake", "parity"],
        )
        n2, k2 = rng.choice([6, 8, 10]), rng.choice([2, 3, 4])
        add(
            f"في غرفة {ar(n2, e)} أشخاص، يقول كل واحد منهم إن {ar(k2, e)} من الباقين أصدقاؤه. "
            f"هل يمكن أن يكون الجميع صادقين؟",
            "نعم",
            ["relation", "handshake", "witness"],
        )
        n3 = rng.choice([4, 5, 6])
        add(
            f"في غرفة {ar(n3, e)} أشخاص، يقول كل واحد منهم إن {ar(n3, e)} من الباقين أصدقاؤه. "
            f"هل يمكن أن يكون الجميع صادقين؟",
            "لا",
            ["relation", "handshake", "degree-bound"],
        )
    return L


def main() -> None:
    n_per = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    m, lg = gen_math(n_per), gen_logic(max(2, n_per // 4))
    with OUT.open("w") as f:
        for i, item in enumerate(m, 1):
            f.write(json.dumps({"id": f"sarmath-{i:03d}", **item}, ensure_ascii=False) + "\n")
        for i, item in enumerate(lg, 1):
            f.write(json.dumps({"id": f"sarlogic-{i:03d}", **item}, ensure_ascii=False) + "\n")
    print(f"wrote {len(m)} Arabic math + {len(lg)} Arabic logic problems to {OUT}")


if __name__ == "__main__":
    main()
