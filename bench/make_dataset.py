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


def main() -> None:
    math_items = gen_math()
    logic_items = gen_logic()
    with OUT.open("w") as f:
        for i, item in enumerate(math_items, 1):
            f.write(json.dumps({"id": f"math-{i:03d}", **item}, ensure_ascii=False) + "\n")
        for i, item in enumerate(logic_items, 1):
            f.write(json.dumps({"id": f"logic-{i:03d}", **item}, ensure_ascii=False) + "\n")
    print(f"wrote {len(math_items)} math + {len(logic_items)} logic problems to {OUT}")


if __name__ == "__main__":
    main()
