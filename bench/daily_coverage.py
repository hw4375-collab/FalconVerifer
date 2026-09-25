"""Deterministic-coverage report for the everyday Arabic dialogue set (no model calls).

For every item of bench/problems_daily_ar.jsonl:
  inference/det:*  — does `arabic_daily.formalize_daily` (plus the older fragments) yield a
                     Lean proposition for the gold answer?  → deterministic coverage
  inference (LLM)  — counted as the honest gap: needs the LLM formalizer
  fact / chat      — the deterministic layer must return None (fail closed): a formalized
                     world fact would be a false alarm waiting to happen

Run:  python bench/daily_coverage.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from falconverifier import arabic, arabic_daily, arabic_word  # noqa: E402

DATA = Path(__file__).parent / "problems_daily_ar.jsonl"


def det_prop(problem: str, answer: str | None) -> str | None:
    if answer is None:
        return None
    hit = (
        arabic.formalize_problem(problem, answer)
        or arabic_word.formalize_word_problem(problem, answer)
        or arabic_daily.formalize_daily(problem, answer)
    )
    return hit[0] if hit else None


def main() -> int:
    items = [json.loads(line) for line in DATA.read_text().splitlines() if line.strip()]
    cov: Counter[str] = Counter()
    tot: Counter[str] = Counter()
    leaks: list[str] = []
    misses: list[str] = []
    for it in items:
        key = it["det"] or ("inference/llm" if it["label"] == "inference" else it["label"])
        tot[key] += 1
        prop = det_prop(it["problem"], it["answer"])
        if it["label"] in ("fact", "chat"):
            if prop or arabic_daily.analyze(it["problem"]):
                leaks.append(it["id"])
        elif prop:
            cov[key] += 1
        elif it["det"]:
            misses.append(f"{it['id']}: {it['problem']}")
    print("| family | items | deterministic Lean proposition |")
    print("|---|---:|---:|")
    for k in sorted(tot):
        n, c = tot[k], cov[k]
        print(f"| {k} | {n} | {c}/{n} ({100 * c / n:.0f}%) |")
    inf = sum(tot[k] for k in tot if k not in ("fact", "chat"))
    infc = sum(cov.values())
    print(
        f"\ninference items: {inf}; deterministic coverage {infc}/{inf} ({100 * infc / inf:.0f}%)"
    )
    print(
        f"fact/chat items formalized by the deterministic layer (must be 0): {len(leaks)} {leaks}"
    )
    for m in misses:
        print("MISS", m)
    return 1 if leaks or misses else 0


if __name__ == "__main__":
    raise SystemExit(main())
