"""Generate bench/problems_ar.jsonl: Arabic (MSA) math word problems + logic items.

Same templates families as the English set, but written in Arabic with Arabic names and
dirham/tafaha vocabulary. Half of the arithmetic items use Eastern Arabic digits (٠-٩) so
the pipeline's digit normalisation is exercised. A subset of items («fragment» tag) is a
bare arithmetic question that lies inside the pregroup grammar's deterministic fragment;
the rest need the LLM formalizer. Run:  python bench/make_dataset_ar.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

rng = random.Random(20260925)
OUT = Path(__file__).parent / "problems_ar.jsonl"

NAMES_M = ["أحمد", "عمر", "يوسف", "خالد", "حمدان", "زايد", "سلطان", "راشد"]
NAMES_F = ["عائشة", "ليلى", "فاطمة", "نور", "سارة", "مريم", "هند"]
ITEMS = ["كتاباً", "قلماً", "تمرة", "كوباً", "بلاطة", "تذكرة", "زجاجة", "صندوقاً", "عملة", "كرسياً"]

_EAST = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def ar(n: int | float, eastern: bool) -> str:
    s = str(n)
    return s.translate(_EAST) if eastern else s


def gen_math() -> list[dict]:
    out: list[dict] = []

    def add(problem: str, answer, tags: list[str], eastern: bool) -> None:
        out.append(
            {
                "problem": problem,
                "answer": str(answer),
                "tags": ["math", "arabic", *tags, *(["eastern-digits"] if eastern else [])],
            }
        )

    # 1. bare arithmetic inside the pregroup fragment
    for i in range(8):
        e = i % 2 == 0
        a, b = rng.randint(13, 98), rng.randint(12, 49)
        add(f"ما هو ناتج {ar(a, e)} × {ar(b, e)}؟", a * b, ["arith", "fragment"], e)
    for i in range(4):
        e = i % 2 == 0
        a, b, c = rng.randint(120, 980), rng.randint(110, 490), rng.randint(20, 99)
        add(
            f"احسب مجموع {ar(a, e)} و {ar(b, e)} ناقص {ar(c, e)}.",
            a + b - c,
            ["arith", "fragment"],
            e,
        )
    for i in range(4):
        e = i % 2 == 0
        p = rng.choice([10, 20, 25, 40, 50, 75])
        base = rng.choice([80, 120, 160, 200, 240, 360, 480])
        add(
            f"كم يساوي {ar(p, e)}٪ من {ar(base, e)}؟",
            base * p // 100,
            ["arith", "percent", "fragment"],
            e,
        )

    # 2. multiplication then subtraction (word problem)
    for i in range(6):
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
    # 3. percentages
    for i in range(5):
        e = i % 2 == 0
        price = rng.choice([80, 120, 150, 200, 240, 360, 400, 500])
        pct = rng.choice([10, 15, 20, 25, 30, 40])
        add(
            f"يبلغ سعر معطف {ar(price, e)} درهماً. خُفِّض سعره بنسبة {ar(pct, e)}٪. "
            f"ما هو السعر الجديد بالدرهم؟",
            price - price * pct // 100,
            ["arith", "percent"],
            e,
        )
    # 4. averages
    for i in range(4):
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
    # 5. division with remainder
    for i in range(4):
        e = i % 2 == 0
        total, per = rng.randint(150, 900), rng.randint(7, 24)
        add(
            f"لدينا {ar(total, e)} تفاحة نضعها في صناديق تتسع كل منها {ar(per, e)} تفاحة. "
            f"كم صندوقاً ممتلئاً نحصل عليه؟",
            total // per,
            ["arith", "division"],
            e,
        )
    # 6. linear equation
    for i in range(4):
        e = i % 2 == 0
        x = rng.randint(6, 40)
        a, b = rng.randint(3, 9), rng.randint(5, 60)
        add(
            f"فكّر {rng.choice(NAMES_M)} في عدد، ضربه في {ar(a, e)} ثم أضاف {ar(b, e)}، فكانت النتيجة "
            f"{ar(a * x + b, e)}. ما هو العدد الأصلي؟",
            x,
            ["algebra", "linear"],
            e,
        )
    # 7. age
    for i in range(3):
        e = i % 2 == 0
        child, k, yrs = rng.randint(5, 14), rng.randint(3, 5), rng.randint(4, 12)
        add(
            f"عمر الأب اليوم {ar(k, e)} أمثال عمر ابنه، وعمر الابن {ar(child, e)} سنوات. "
            f"كم سيكون عمر الأب بعد {ar(yrs, e)} سنوات؟",
            k * child + yrs,
            ["algebra", "age"],
            e,
        )
    # 8. money with change
    for i in range(4):
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
    # 9. compound percent (hard)
    for i in range(3):
        e = i % 2 == 0
        price = rng.choice([800, 1200, 1500, 2400])
        p1, p2 = rng.choice([10, 20, 25]), rng.choice([10, 20])
        add(
            f"يبلغ سعر هاتف {ar(price, e)} درهماً. خُفِّض بنسبة {ar(p1, e)}٪ ثم خُفِّض السعر الجديد "
            f"بنسبة {ar(p2, e)}٪ أخرى. ما هو السعر النهائي بالدرهم؟",
            price * (100 - p1) * (100 - p2) // 10000,
            ["arith", "compound-percent", "hard"],
            e,
        )
    # 10. order of operations
    for i in range(3):
        e = i % 2 == 0
        a, b, c, d = rng.randint(10, 60), rng.randint(3, 12), rng.randint(3, 12), rng.randint(2, 9)
        add(
            f"احسب قيمة {ar(a, e)} + {ar(b, e)} × {ar(c, e)} − {ar(d, e)}² باتباع ترتيب العمليات.",
            a + b * c - d * d,
            ["arith", "order-of-operations", "hard"],
            e,
        )
    return out


def gen_logic() -> list[dict]:
    L: list[dict] = []

    def add(problem: str, answer: str, tags: list[str]) -> None:
        L.append(
            {
                "problem": problem + " أجب بنعم أو لا.",
                "answer": answer,
                "tags": ["logic", "arabic", *tags],
            }
        )

    # syllogisms — valid
    add(
        "كل المربعات مستطيلات، وكل المستطيلات أشكال رباعية. هل يلزم أن كل المربعات أشكال رباعية؟",
        "نعم",
        ["syllogism", "valid"],
    )
    add(
        "كل الأطباء متعلمون، وبعض المتعلمين فقراء. هل يلزم أن بعض الأطباء فقراء؟",
        "لا",
        ["syllogism", "invalid", "undistributed-middle"],
    )
    add(
        "لا شيء من الطيور ثدييات، وكل الخفافيش ثدييات. هل يلزم أن لا شيء من الخفافيش طيور؟",
        "نعم",
        ["syllogism", "valid"],
    )
    add(
        "كل الطلاب في الصف يتكلمون العربية، وسلطان طالب في الصف. هل يلزم أن سلطان يتكلم العربية؟",
        "نعم",
        ["syllogism", "valid"],
    )
    add(
        "بعض الكتب مفيدة، وبعض المفيد غالٍ. هل يلزم أن بعض الكتب غالية؟",
        "لا",
        ["syllogism", "invalid"],
    )
    add(
        "كل المربعات مستطيلات، وبعض المستطيلات ليست مربعات. هل يلزم أن بعض المربعات ليست مستطيلات؟",
        "لا",
        ["syllogism", "invalid", "illicit-conversion"],
    )
    add(
        "كل الأعداد الأولية الأكبر من ٢ فردية، و٩ فردي. هل يلزم أن ٩ عدد أولي؟",
        "لا",
        ["syllogism", "invalid", "affirming-consequent"],
    )
    add(
        "لا أحد من الطلاب الغائبين نجح، وخالد نجح. هل يلزم أن خالد لم يكن غائباً؟",
        "نعم",
        ["syllogism", "valid"],
    )
    # propositional
    add(
        "إذا أمطرت فإن الأرض تبتل. الأرض مبتلة. هل يلزم أنها أمطرت؟",
        "لا",
        ["propositional", "affirming-consequent"],
    )
    add(
        "إذا أمطرت فإن الأرض تبتل. الأرض ليست مبتلة. هل يلزم أنها لم تمطر؟",
        "نعم",
        ["propositional", "modus-tollens"],
    )
    add(
        "إذا درست فاطمة فإنها تنجح. لم تدرس فاطمة. هل يلزم أنها لم تنجح؟",
        "لا",
        ["propositional", "denying-antecedent"],
    )
    add(
        "إذا كان العدد زوجياً فإنه يقبل القسمة على ٢. العدد ١٨ زوجي. هل يلزم أن ١٨ يقبل القسمة على ٢؟",
        "نعم",
        ["propositional", "modus-ponens"],
    )
    add(
        "إما أن يكون المفتاح في الحقيبة أو في السيارة. المفتاح ليس في الحقيبة. هل يلزم أنه في السيارة؟",
        "نعم",
        ["propositional", "disjunctive-syllogism"],
    )
    add(
        "إما أن يكون المفتاح في الحقيبة أو في السيارة. المفتاح في الحقيبة. هل يلزم أنه ليس في السيارة؟",
        "لا",
        ["propositional", "inclusive-or"],
    )
    add(
        "إذا كان أحمد في دبي فإنه في الإمارات. إذا كان في الإمارات فإنه في آسيا. هل يلزم أنه إذا كان في دبي فإنه في آسيا؟",
        "نعم",
        ["propositional", "hypothetical-syllogism"],
    )
    # ordering
    add(
        "عمر أطول من يوسف، ويوسف أطول من خالد. هل يلزم أن عمر أطول من خالد؟",
        "نعم",
        ["ordering", "transitivity"],
    )
    add(
        "عمر أطول من يوسف، وعمر أطول من خالد. هل يلزم أن يوسف أطول من خالد؟",
        "لا",
        ["ordering", "invalid"],
    )
    add(
        "ليلى أكبر سناً من نور، ونور أكبر سناً من سارة. هل يلزم أن سارة أصغر من ليلى؟",
        "نعم",
        ["ordering", "transitivity"],
    )
    add(
        "أحمد يجلس على يمين خالد مباشرة، وخالد على يمين عمر مباشرة. هل يلزم أن عمر على يسار أحمد؟",
        "نعم",
        ["ordering", "spatial"],
    )
    # arithmetic-flavoured logic (divisibility)
    add(
        "كل عدد يقبل القسمة على ٦ يقبل القسمة على ٣. العدد ٤٥ يقبل القسمة على ٣. هل يلزم أن ٤٥ يقبل القسمة على ٦؟",
        "لا",
        ["divisibility", "affirming-consequent"],
    )
    add(
        "كل عدد يقبل القسمة على ٦ يقبل القسمة على ٣. العدد ٤٨ يقبل القسمة على ٦. هل يلزم أن ٤٨ يقبل القسمة على ٣؟",
        "نعم",
        ["divisibility", "modus-ponens"],
    )
    add("مجموع عددين فرديين زوجي دائماً. هل يلزم أن ٧ + ٩ زوجي؟", "نعم", ["parity", "valid"])
    add(
        "إذا كان حاصل ضرب عددين صحيحين زوجياً فإن أحدهما على الأقل زوجي. حاصل ضرب أ × ب يساوي ٣٠. هل يلزم أن أ زوجي؟",
        "لا",
        ["parity", "invalid"],
    )
    add(
        "جميع الأعداد الأولية الأكبر من ٢ فردية، و١٥ فردي وأكبر من ٢. هل يلزم أن ١٥ عدد أولي؟",
        "لا",
        ["prime", "affirming-consequent"],
    )
    # symmetric relations / counting (handshake lemma) — the regular-graph fragment
    add(
        "خمسة طلاب يجلسون في الفصل، ويقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟",
        "نعم",
        ["relation", "handshake", "parity"],
    )
    add(
        "ستة أشخاص، كل واحد منهم صديق لثلاثة من الآخرين بالضبط والصداقة متبادلة. هل يمكن ذلك؟",
        "نعم",
        ["relation", "handshake", "witness"],
    )
    add(
        "في حفلة ٧ ضيوف، صافح كل ضيف بالضبط ٣ من الضيوف الآخرين. هل يمكن ذلك؟",
        "لا",
        ["relation", "handshake", "parity", "eastern-digits"],
    )
    add(
        "في حفلة ٨ ضيوف، صافح كل ضيف بالضبط ٣ من الضيوف الآخرين. هل يمكن ذلك؟",
        "نعم",
        ["relation", "handshake", "witness", "eastern-digits"],
    )
    add(
        "تسعة لاعبين، يقول كل لاعب إنه لعب مباراة مع خمسة من اللاعبين الآخرين بالضبط. هل يلزم أن أحدهم يكذب؟",
        "نعم",
        ["relation", "handshake", "parity"],
    )
    add(
        "عشرة لاعبين، لعب كل لاعب مباراة مع ثلاثة من اللاعبين الآخرين بالضبط. هل يمكن ذلك؟",
        "نعم",
        ["relation", "handshake", "witness"],
    )
    add(
        "أربعة طلاب، ويقول كل طالب إن له أربعة أصدقاء بينهم. هل يلزم أن أحدهم يكذب؟",
        "نعم",
        ["relation", "degree-bound"],
    )
    add(
        "ستة أشخاص، كل واحد منهم يعرف اثنين من الآخرين بالضبط والتعارف متبادل. هل يمكن ذلك؟",
        "نعم",
        ["relation", "handshake", "witness"],
    )
    add(
        "سبعة طلاب، ويقول كل واحد منهم إن أربعة من الستة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟",
        "لا",
        ["relation", "handshake", "witness"],
    )
    add(
        "أحد عشر ضيفاً، صافح كل ضيف بالضبط ٥ من الضيوف الآخرين. هل يمكن ذلك؟",
        "لا",
        ["relation", "handshake", "parity", "eastern-digits"],
    )
    return L


def main() -> None:
    m, lg = gen_math(), gen_logic()
    with OUT.open("w") as f:
        for i, item in enumerate(m, 1):
            f.write(json.dumps({"id": f"armath-{i:03d}", **item}, ensure_ascii=False) + "\n")
        for i, item in enumerate(lg, 1):
            f.write(json.dumps({"id": f"arlogic-{i:03d}", **item}, ensure_ascii=False) + "\n")
    print(f"wrote {len(m)} Arabic math + {len(lg)} Arabic logic problems to {OUT}")


if __name__ == "__main__":
    main()
