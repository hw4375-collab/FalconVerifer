"""Generate bench/problems.jsonl: basic-math word problems + logical-reasoning items.

Arithmetic problems are generated from templates with a fixed seed so answers are exact.
Logic problems are hand-written (valid and invalid syllogisms, propositional fallacies,
ordering puzzles). Run:  python bench/make_dataset.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

rng = random.Random(20260924)
OUT = Path(__file__).parent / "problems.jsonl"
OUT_HARD = Path(__file__).parent / "problems_hard.jsonl"

NAMES = ["Aisha", "Omar", "Layla", "Yousef", "Fatima", "Hamdan", "Noor", "Khalid", "Sara", "Zayed"]
ITEMS = [
    "books",
    "pens",
    "dates",
    "cups",
    "tiles",
    "tickets",
    "bottles",
    "boxes",
    "coins",
    "chairs",
]


def pick_name() -> str:
    return rng.choice(NAMES)


def gen_math() -> list[dict]:
    out: list[dict] = []

    def add(problem: str, answer, tags: list[str]) -> None:
        out.append({"problem": problem, "answer": str(answer), "tags": ["math", *tags]})

    # 1. multi-digit multiplication then subtraction
    for _ in range(6):
        a, b, c = rng.randint(23, 98), rng.randint(12, 49), rng.randint(50, 400)
        n, it = pick_name(), rng.choice(ITEMS)
        add(
            f"{n} buys {a} packs of {it} with {b} in each pack, then gives away {c} of them. "
            f"How many {it} does {n} have left?",
            a * b - c,
            ["arith", "multiply"],
        )
    # 2. two products compared
    for _ in range(5):
        a, b, c, d = (
            rng.randint(14, 59),
            rng.randint(11, 39),
            rng.randint(14, 59),
            rng.randint(11, 39),
        )
        while a * b == c * d:
            d += 1
        add(
            f"Warehouse A stores {a} crates of {b} kg each. Warehouse B stores {c} crates of {d} kg "
            f"each. How many more kilograms does the heavier warehouse hold than the lighter one?",
            abs(a * b - c * d),
            ["arith", "compare"],
        )
    # 3. percentages
    for _ in range(6):
        price = rng.choice([120, 250, 360, 480, 640, 750, 880, 1250])
        pct = rng.choice([5, 10, 12, 15, 20, 25, 30, 35, 40])
        add(
            f"A laptop costs {price} dirhams. During a sale its price is reduced by {pct}%. "
            f"What is the sale price in dirhams?",
            price * (100 - pct) // 100
            if price * (100 - pct) % 100 == 0
            else price * (100 - pct) / 100,
            ["arith", "percent"],
        )
    for _ in range(3):
        base = rng.choice([80, 150, 200, 320, 450])
        pct = rng.choice([10, 20, 25, 40, 50, 75])
        add(
            f"A town had {base} shops last year. This year the number of shops increased by {pct}%. "
            f"How many shops are there this year?",
            base + base * pct // 100,
            ["arith", "percent"],
        )
    # 4. averages
    for _ in range(4):
        k = rng.randint(4, 6)
        vals = [rng.randint(40, 99) for _ in range(k)]
        # force integer mean
        total = sum(vals)
        vals[-1] += (-total) % k
        add(
            f"A student scored {', '.join(map(str, vals[:-1]))} and {vals[-1]} on {k} tests. "
            f"What is the student's average score?",
            sum(vals) // k,
            ["arith", "average"],
        )
    # 5. division with remainder
    for _ in range(4):
        total, per = rng.randint(200, 999), rng.randint(7, 24)
        add(
            f"{total} {rng.choice(ITEMS)} are packed into boxes of {per}. How many full boxes are "
            f"there, and how many are left over? Give the answer as the number left over.",
            total % per,
            ["arith", "remainder"],
        )
    # 6. unit / rate problems
    for _ in range(4):
        speed, h, m = rng.randint(48, 96), rng.randint(2, 5), rng.choice([15, 30, 45])
        dist = speed * h + speed * m / 60
        add(
            f"A car travels at a constant {speed} km/h for {h} hours and {m} minutes. "
            f"How many kilometres does it travel?",
            int(dist) if dist == int(dist) else dist,
            ["arith", "rate"],
        )
    # 7. linear equation word problems
    for _ in range(5):
        x = rng.randint(6, 40)
        a, b = rng.randint(3, 9), rng.randint(5, 60)
        add(
            f"{pick_name()} thinks of a number, multiplies it by {a}, and adds {b}. The result is "
            f"{a * x + b}. What was the original number?",
            x,
            ["algebra", "linear"],
        )
    # 8. age problems
    for _ in range(3):
        child = rng.randint(5, 14)
        k = rng.randint(3, 5)
        yrs = rng.randint(4, 12)
        add(
            f"Today a father is {k} times as old as his son. The son is {child} years old. "
            f"How old will the father be in {yrs} years?",
            k * child + yrs,
            ["algebra", "age"],
        )
    # 9. multi-step money
    for _ in range(5):
        n1, p1, n2, p2, paid = (
            rng.randint(3, 12),
            rng.randint(7, 45),
            rng.randint(2, 9),
            rng.randint(11, 60),
            rng.choice([500, 600, 800, 1000]),
        )
        cost = n1 * p1 + n2 * p2
        if cost >= paid:
            paid = ((cost // 100) + 2) * 100
        add(
            f"{pick_name()} buys {n1} notebooks at {p1} dirhams each and {n2} pens at {p2} dirhams "
            f"each, paying with {paid} dirhams. How much change does {pick_name()} receive?",
            paid - cost,
            ["arith", "money"],
        )
    # 10. squares / powers / fractions
    for _ in range(3):
        a = rng.randint(13, 39)
        add(f"What is {a} squared minus {a}?", a * a - a, ["arith", "power"])
    for _ in range(3):
        d = rng.choice([4, 5, 8, 10, 20, 25])
        num = rng.randint(1, d - 1)
        tot = d * rng.randint(12, 60)
        add(
            f"A tank holds {tot} litres when full. It is currently {num}/{d} full. "
            f"How many litres must be added to fill it?",
            tot - tot * num // d,
            ["arith", "fraction"],
        )
    return out


def gen_logic() -> list[dict]:
    L: list[dict] = []

    def add(problem: str, answer: str, tags: list[str]) -> None:
        L.append({"problem": problem, "answer": answer, "tags": ["logic", *tags]})

    q = " Does the conclusion necessarily follow from the premises? Answer Yes or No."
    # Valid syllogisms
    add(
        "All engineers are graduates. All graduates can read. Conclusion: all engineers can read."
        + q,
        "Yes",
        ["syllogism", "valid"],
    )
    add(
        "No reptiles are mammals. All snakes are reptiles. Conclusion: no snakes are mammals." + q,
        "Yes",
        ["syllogism", "valid"],
    )
    add(
        "All pilots are trained. Some pilots are women. Conclusion: some women are trained." + q,
        "Yes",
        ["syllogism", "valid"],
    )
    add(
        "Some artists are teachers. All teachers are patient. Conclusion: some artists are patient."
        + q,
        "Yes",
        ["syllogism", "valid"],
    )
    add(
        "No fish are birds. Some pets are fish. Conclusion: some pets are not birds." + q,
        "Yes",
        ["syllogism", "valid"],
    )
    add(
        "All roses are flowers. No flowers are minerals. Conclusion: no roses are minerals." + q,
        "Yes",
        ["syllogism", "valid"],
    )
    add(
        "All A are B. All B are C. All C are D. Conclusion: all A are D." + q,
        "Yes",
        ["syllogism", "valid"],
    )
    add(
        "Every student in the class passed. Amal is a student in the class. Conclusion: Amal passed."
        + q,
        "Yes",
        ["syllogism", "valid"],
    )
    # Invalid syllogisms (classic traps)
    add(
        "All cats are mammals. Some mammals are dogs. Conclusion: some cats are dogs." + q,
        "No",
        ["syllogism", "invalid"],
    )
    add(
        "All doctors are educated. Some educated people are wealthy. Conclusion: some doctors are wealthy."
        + q,
        "No",
        ["syllogism", "invalid"],
    )
    add(
        "All squares are rectangles. Some rectangles are not squares. Conclusion: some squares are not rectangles."
        + q,
        "No",
        ["syllogism", "invalid"],
    )
    add(
        "Some birds can fly. Penguins are birds. Conclusion: penguins can fly." + q,
        "No",
        ["syllogism", "invalid"],
    )
    add(
        "All lawyers are argumentative. Karim is argumentative. Conclusion: Karim is a lawyer." + q,
        "No",
        ["syllogism", "invalid"],
    )
    add(
        "No cars are boats. No boats are planes. Conclusion: no cars are planes." + q,
        "No",
        ["syllogism", "invalid"],
    )
    add(
        "Some managers are engineers. Some engineers are musicians. Conclusion: some managers are musicians."
        + q,
        "No",
        ["syllogism", "invalid"],
    )
    add(
        "All athletes exercise. Some people who exercise are unhealthy. Conclusion: some athletes are unhealthy."
        + q,
        "No",
        ["syllogism", "invalid"],
    )
    add("All A are B. Some B are C. Conclusion: some A are C." + q, "No", ["syllogism", "invalid"])
    add(
        "Some A are not B. All C are B. Conclusion: some C are not A." + q,
        "No",
        ["syllogism", "invalid"],
    )
    # Propositional
    add(
        "If it rains, the street is wet. The street is wet. Conclusion: it rained." + q,
        "No",
        ["propositional", "affirming-consequent"],
    )
    add(
        "If it rains, the street is wet. It did not rain. Conclusion: the street is not wet." + q,
        "No",
        ["propositional", "denying-antecedent"],
    )
    add(
        "If it rains, the street is wet. The street is not wet. Conclusion: it did not rain." + q,
        "Yes",
        ["propositional", "modus-tollens"],
    )
    add(
        "If the alarm rings, everyone leaves. The alarm rings. Conclusion: everyone leaves." + q,
        "Yes",
        ["propositional", "modus-ponens"],
    )
    add(
        "Either the file is corrupt or the disk is full. The disk is not full. Conclusion: the file is corrupt."
        + q,
        "Yes",
        ["propositional", "disjunctive"],
    )
    add(
        "Either the file is corrupt or the disk is full. The file is corrupt. Conclusion: the disk is not full."
        + q,
        "No",
        ["propositional", "disjunctive"],
    )
    add("If P then Q. If Q then R. Conclusion: if P then R." + q, "Yes", ["propositional", "chain"])
    add(
        "If P then Q. If R then Q. Q is true. Conclusion: P is true." + q,
        "No",
        ["propositional", "invalid"],
    )
    add("P or Q. Not P. Not Q. Conclusion: R." + q, "Yes", ["propositional", "explosion"])
    add(
        "If P then Q. Q is true. Conclusion: P and Q are both true." + q,
        "No",
        ["propositional", "invalid"],
    )
    # Ordering / comparison
    add(
        "Ali is taller than Badr. Badr is taller than Chen. Conclusion: Ali is taller than Chen."
        + q,
        "Yes",
        ["ordering", "valid"],
    )
    add(
        "Ali is taller than Badr. Ali is taller than Chen. Conclusion: Badr is taller than Chen."
        + q,
        "No",
        ["ordering", "invalid"],
    )
    add(
        "Dana finished before Eman. Eman finished before Farah. Farah finished before Ghada. Conclusion: Dana finished before Ghada."
        + q,
        "Yes",
        ["ordering", "valid"],
    )
    add(
        "Box X is heavier than box Y. Box Z is lighter than box Y. Conclusion: box Z is lighter than box X."
        + q,
        "Yes",
        ["ordering", "valid"],
    )
    add(
        "Box X is heavier than box Y. Box Z is heavier than box Y. Conclusion: box X is heavier than box Z."
        + q,
        "No",
        ["ordering", "invalid"],
    )
    # Numeric logic
    add(
        "A number is divisible by 6. Conclusion: the number is divisible by 3." + q,
        "Yes",
        ["number", "valid"],
    )
    add(
        "A number is divisible by 3. Conclusion: the number is divisible by 6." + q,
        "No",
        ["number", "invalid"],
    )
    add("n is an even integer. Conclusion: n squared is even." + q, "Yes", ["number", "valid"])
    add(
        "x and y are integers with x > y. Conclusion: x squared is greater than y squared." + q,
        "No",
        ["number", "invalid"],
    )
    add(
        "x is a positive integer greater than 1. Conclusion: x squared is greater than x." + q,
        "Yes",
        ["number", "valid"],
    )
    return L


def gen_hard_math() -> list[dict]:
    """Harder tier: long carries, 3x3-digit products, compound percentages, order of operations."""
    out: list[dict] = []

    def add(problem: str, answer, tags: list[str]) -> None:
        out.append({"problem": problem, "answer": str(answer), "tags": ["math", "hard", *tags]})

    for _ in range(6):
        a, b = rng.randint(203, 987), rng.randint(112, 689)
        add(f"Compute {a} × {b}.", a * b, ["arith", "multiply3"])
    for _ in range(4):
        a, b, c = rng.randint(1203, 9876), rng.randint(2004, 8765), rng.randint(105, 998)
        add(f"Compute {a} + {b} - {c}.", a + b - c, ["arith", "carry"])
    for _ in range(4):
        a, b, c, d = (
            rng.randint(12, 49),
            rng.randint(13, 47),
            rng.randint(11, 39),
            rng.randint(2, 9),
        )
        add(
            f"Evaluate {a} + {b} × {c} - {d}² using the standard order of operations.",
            a + b * c - d * d,
            ["arith", "order-of-operations"],
        )
    for _ in range(4):
        price = rng.choice([800, 1200, 1500, 2400, 3200])
        p1, p2 = rng.choice([10, 20, 25]), rng.choice([10, 15, 20])
        ans = price * (100 - p1) * (100 - p2) / 10000
        add(
            f"A phone costs {price} dirhams. It is discounted by {p1}%, and then the reduced price is "
            f"discounted by a further {p2}%. What is the final price in dirhams?",
            int(ans) if ans == int(ans) else ans,
            ["arith", "compound-percent"],
        )
    for _ in range(4):
        k = rng.randint(5, 8)
        vals = [rng.randint(40, 99) for _ in range(k)]
        vals[-1] += (-sum(vals)) % k
        old = vals[0]
        new = old + rng.choice([-k * 3, k * 2, k * 4])
        add(
            f"The average of {k} numbers {', '.join(map(str, vals))} is computed. Then the number "
            f"{old} is replaced by {new}. What is the new average?",
            (sum(vals) - old + new) // k,
            ["arith", "average-change"],
        )
    for _ in range(4):
        n, m = rng.randint(1000, 9999), rng.randint(13, 47)
        add(f"What is the remainder when {n} is divided by {m}?", n % m, ["arith", "remainder"])
    for _ in range(3):
        x = rng.randint(11, 60)
        add(
            f"The sum of three consecutive integers is {3 * x + 3}. What is the largest of them?",
            x + 2,
            ["algebra", "consecutive"],
        )
    for a, b in rng.sample([(6, 12), (4, 12), (10, 15), (12, 24), (3, 6), (20, 30)], 3):
        add(
            f"Pipe A fills a tank in {a} hours and pipe B fills it in {b} hours. Working together, "
            f"how many hours do they take?",
            (a * b) // (a + b),
            ["algebra", "work-rate"],
        )
    for _ in range(3):
        a, d = rng.randint(3, 15), rng.randint(2, 9)
        n = rng.randint(15, 40)
        add(
            f"An arithmetic sequence starts at {a} and increases by {d} each term. "
            f"What is the {n}th term?",
            a + (n - 1) * d,
            ["algebra", "sequence"],
        )
    for _ in range(3):
        s, cp = rng.randint(4, 9) * 10, rng.choice([2, 3, 4, 5])
        add(
            f"A rectangle has perimeter {2 * (s + s * cp)} and its length is {cp} times its width. "
            f"What is its area?",
            s * s * cp,
            ["algebra", "geometry"],
        )
    return out


def gen_hard_logic() -> list[dict]:
    L: list[dict] = []

    def add(problem: str, answer: str, tags: list[str]) -> None:
        L.append({"problem": problem, "answer": answer, "tags": ["logic", "hard", *tags]})

    q = " Does the conclusion necessarily follow from the premises? Answer Yes or No."
    items: list[tuple[str, str, list[str]]] = [
        (
            "Only members may enter. Rania entered. Conclusion: Rania is a member.",
            "Yes",
            ["only-if", "valid"],
        ),
        (
            "Only members may enter. Rania is a member. Conclusion: Rania entered.",
            "No",
            ["only-if", "invalid"],
        ),
        (
            "Unless it rains, the match is played. The match was not played. Conclusion: it rained.",
            "Yes",
            ["unless", "valid"],
        ),
        (
            "Unless it rains, the match is played. It rained. Conclusion: the match was not played.",
            "No",
            ["unless", "invalid"],
        ),
        (
            "If x is a multiple of 4 then x is even. x is even. Conclusion: x is a multiple of 4.",
            "No",
            ["number", "affirming-consequent"],
        ),
        (
            "Every multiple of 12 is a multiple of 4. Every multiple of 4 is even. 84 is a multiple of 12. Conclusion: 84 is even.",
            "Yes",
            ["number", "chain"],
        ),
        (
            "No prime greater than 2 is even. 91 is odd. Conclusion: 91 is prime.",
            "No",
            ["number", "invalid"],
        ),
        (
            "All squares of integers are non-negative. n² = -4 for some integer n. Conclusion: 0 = 1.",
            "Yes",
            ["number", "explosion"],
        ),
        (
            "Some students study Lean. All who study Lean study logic. Some who study logic study Python. Conclusion: some students study Python.",
            "No",
            ["syllogism", "invalid"],
        ),
        (
            "All A are B. No B are C. Some D are C. Conclusion: some D are not A.",
            "Yes",
            ["syllogism", "valid"],
        ),
        (
            "All A are B. No B are C. Some D are not C. Conclusion: some D are A.",
            "No",
            ["syllogism", "invalid"],
        ),
        (
            "Some A are B. Some B are C. Some C are D. Conclusion: some A are D.",
            "No",
            ["syllogism", "invalid"],
        ),
        (
            "No A are B. All C are A. Some D are C. Conclusion: some D are not B.",
            "Yes",
            ["syllogism", "valid"],
        ),
        (
            "Exactly one of P and Q is true. P is true. Conclusion: Q is false.",
            "Yes",
            ["xor", "valid"],
        ),
        (
            "At least one of P and Q is true. P is true. Conclusion: Q is false.",
            "No",
            ["or", "invalid"],
        ),
        (
            "If P then Q. If not P then R. Conclusion: Q or R.",
            "Yes",
            ["propositional", "case-split"],
        ),
        (
            "If P then Q. If P then R. Q and R are true. Conclusion: P is true.",
            "No",
            ["propositional", "invalid"],
        ),
        (
            "P if and only if Q. Q if and only if R. Not R. Conclusion: not P.",
            "Yes",
            ["iff", "valid"],
        ),
        ("If P then (Q or R). Not Q. P. Conclusion: R.", "Yes", ["propositional", "valid"]),
        (
            "If P then (Q and R). Not Q. Conclusion: not P.",
            "Yes",
            ["propositional", "modus-tollens"],
        ),
        ("If (P and Q) then R. Not R. P. Conclusion: not Q.", "Yes", ["propositional", "valid"]),
        (
            "If (P or Q) then R. Not R. Conclusion: not P and not Q.",
            "Yes",
            ["propositional", "valid"],
        ),
        ("If (P and Q) then R. Not R. Conclusion: not P.", "No", ["propositional", "invalid"]),
        (
            "Ahmed is older than Bilal. Bilal is older than Carla. Dina is younger than Carla. Ehab is older than Ahmed. Conclusion: Dina is the youngest of the five.",
            "Yes",
            ["ordering", "valid"],
        ),
        (
            "Ahmed is older than Bilal. Carla is older than Bilal. Dina is younger than Ahmed. Conclusion: Carla is older than Dina.",
            "No",
            ["ordering", "invalid"],
        ),
        (
            "Five runners: Amal finished before Basim. Basim finished before Chan. Dalia finished after Chan. Emad finished before Amal. Conclusion: Emad finished first.",
            "Yes",
            ["ordering", "valid"],
        ),
        (
            "Five runners: Amal finished before Basim. Chan finished before Basim. Dalia finished after Basim. Conclusion: Amal finished before Chan.",
            "No",
            ["ordering", "invalid"],
        ),
        (
            "x and y are positive integers with x > y. Conclusion: x² > y².",
            "Yes",
            ["number", "valid"],
        ),
        (
            "x and y are real numbers with x > y. Conclusion: 1/x < 1/y.",
            "No",
            ["number", "invalid"],
        ),
        (
            "x and y are integers and x·y is even. Conclusion: x is even.",
            "No",
            ["number", "invalid"],
        ),
        ("x and y are integers and x·y is odd. Conclusion: x is odd.", "Yes", ["number", "valid"]),
        (
            "n is an integer and n² is divisible by 4. Conclusion: n is divisible by 4.",
            "No",
            ["number", "invalid"],
        ),
        (
            "n is an integer and n is divisible by both 4 and 6. Conclusion: n is divisible by 24.",
            "No",
            ["number", "invalid"],
        ),
        (
            "n is an integer and n is divisible by both 3 and 8. Conclusion: n is divisible by 24.",
            "Yes",
            ["number", "valid"],
        ),
        (
            "Every employee who is late is fined. Nobody was fined today. Conclusion: nobody was late today.",
            "Yes",
            ["quantifier", "modus-tollens"],
        ),
        (
            "Every employee who is late is fined. Sami was fined today. Conclusion: Sami was late today.",
            "No",
            ["quantifier", "affirming-consequent"],
        ),
        (
            "Some cities have a metro. Every city with a metro has over a million residents. Conclusion: every city has over a million residents.",
            "No",
            ["quantifier", "invalid"],
        ),
        (
            "There is a student who passed every exam. Conclusion: every exam was passed by at least one student.",
            "Yes",
            ["quantifier", "valid"],
        ),
        (
            "Every exam was passed by at least one student. Conclusion: there is a student who passed every exam.",
            "No",
            ["quantifier", "swap"],
        ),
        ("Not all birds can fly. Conclusion: no birds can fly.", "No", ["quantifier", "invalid"]),
    ]
    for p, a, t in items:
        add(p + q, a, t)
    return L


def main() -> None:
    math_items = gen_math()
    logic_items = gen_logic()
    with OUT.open("w") as f:
        for i, item in enumerate(math_items, 1):
            f.write(json.dumps({"id": f"math-{i:03d}", **item}, ensure_ascii=False) + "\n")
        for i, item in enumerate(logic_items, 1):
            f.write(json.dumps({"id": f"logic-{i:03d}", **item}, ensure_ascii=False) + "\n")
    print(f"wrote {len(math_items)} math + {len(logic_items)} logic problems to {OUT}")

    hm, hl = gen_hard_math(), gen_hard_logic()
    with OUT_HARD.open("w") as f:
        for i, item in enumerate(hm, 1):
            f.write(json.dumps({"id": f"hmath-{i:03d}", **item}, ensure_ascii=False) + "\n")
        for i, item in enumerate(hl, 1):
            f.write(json.dumps({"id": f"hlogic-{i:03d}", **item}, ensure_ascii=False) + "\n")
    print(f"wrote {len(hm)} hard math + {len(hl)} hard logic problems to {OUT_HARD}")


if __name__ == "__main__":
    main()
