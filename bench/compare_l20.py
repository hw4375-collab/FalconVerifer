"""Paired EN/AR comparison for the 20-item logic set (bench/problems_logic20_{en,ar}.jsonl).

    python bench/compare_l20.py [EN_RUN_DIR AR_RUN_DIR]

Defaults to the newest run under bench/results/l20_en and bench/results/l20_ar. Prints, per arm:
undecided rate on the *first* round (the raw formalize→Lean pass, before any feedback), step-level
undecided rate over checkable steps, refutations discarded by the faithfulness audit, accuracy,
detection/fix/false-alarm/regression counts. Markdown table on stdout.
"""

from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

DISCARD = "discarded"


def latest(pattern: str) -> Path:
    runs = sorted(glob.glob(pattern))
    if not runs:
        sys.exit(f"no runs match {pattern}")
    return Path(runs[-1])


def arm(run: Path) -> dict[str, object]:
    rows = json.loads((run / "results.json").read_text())
    rows = rows if isinstance(rows, list) else rows.get("rows") or rows.get("results")
    traces = [json.loads(p.read_text()) for p in sorted(run.glob("l20-*.json"))]
    n = len(traces)

    r1_final = Counter()
    r1_missing = 0
    steps = Counter()
    step_discards = final_discards = raw_step_refuted = raw_final_refuted = 0
    rounds = 0
    for t in traces:
        first = t["rounds"][0]
        rep = first["report"]
        if first["answer"]["final_answer"] is None:
            r1_missing += 1
        r1_final[rep["final_answer_verdict"]] += 1
        for r in t["rounds"]:
            rounds += 1
            rep = r["report"]
            fd = rep.get("final_answer_detail") or ""
            if rep["final_answer_verdict"] == "refuted":
                raw_final_refuted += 1
            if DISCARD in fd:
                final_discards += 1
                raw_final_refuted += 1
            for s in rep["steps"]:
                steps[s["verdict"]] += 1
                d = s.get("detail") or ""
                if s["verdict"] == "refuted":
                    raw_step_refuted += 1
                if DISCARD in d:
                    step_discards += 1
                    raw_step_refuted += 1

    checkable = sum(v for k, v in steps.items() if k != "skipped")
    status = Counter(t["status"] for t in traces)
    base_ok = sum(1 for r in rows if r.get("baseline_correct"))
    final_ok = sum(1 for r in rows if r.get("final_correct"))
    base_wrong = [r for r in rows if not r.get("baseline_correct")]
    detected = sum(1 for r in base_wrong if r.get("status") != "verified" or r.get("rounds", 1) > 1)
    fixed = sum(1 for r in base_wrong if r.get("final_correct"))
    false_alarm = sum(1 for r in rows if r.get("baseline_correct") and r.get("rounds", 1) > 1)
    regress = sum(1 for r in rows if r.get("baseline_correct") and not r.get("final_correct"))
    return {
        "n": n,
        "rounds": rounds,
        "r1_undecided": r1_final["unknown"] + r1_final["ill_formed"] + r1_final["skipped"],
        "r1_missing_final": r1_missing,
        "checkable_steps": checkable,
        "step_unknown": steps["unknown"] + steps["ill_formed"],
        "raw_step_refuted": raw_step_refuted,
        "step_discards": step_discards,
        "raw_final_refuted": raw_final_refuted,
        "final_discards": final_discards,
        "status": dict(status),
        "baseline_ok": base_ok,
        "final_ok": final_ok,
        "wrong": len(base_wrong),
        "detected": detected,
        "fixed": fixed,
        "false_alarm": false_alarm,
        "regressions": regress,
    }


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else f"{a}/0"


def main() -> None:
    if len(sys.argv) == 3:
        en, ar = Path(sys.argv[1]), Path(sys.argv[2])
    else:
        en, ar = latest("bench/results/l20_en/run_*"), latest("bench/results/l20_ar/run_*")
    E, A = arm(en), arm(ar)
    print(f"EN run: `{en}`  ·  AR run: `{ar}`\n")
    print("| metric | English | Arabic |")
    print("|---|---|---|")
    rows = [
        ("problems / rounds", f"{E['n']} / {E['rounds']}", f"{A['n']} / {A['rounds']}"),
        (
            "round-1 final answer undecided (unknown+ill_formed+skipped)",
            pct(E["r1_undecided"], E["n"]),
            pct(A["r1_undecided"], A["n"]),
        ),
        ("round-1 final answer missing", str(E["r1_missing_final"]), str(A["r1_missing_final"])),
        (
            "step undecided over checkable steps",
            pct(E["step_unknown"], E["checkable_steps"]),
            pct(A["step_unknown"], A["checkable_steps"]),
        ),
        (
            "step refutations discarded by faithfulness audit",
            pct(E["step_discards"], E["raw_step_refuted"]),
            pct(A["step_discards"], A["raw_step_refuted"]),
        ),
        (
            "final-answer refutations discarded by audit",
            pct(E["final_discards"], E["raw_final_refuted"]),
            pct(A["final_discards"], A["raw_final_refuted"]),
        ),
        ("trace status", str(E["status"]), str(A["status"])),
        ("baseline correct", pct(E["baseline_ok"], E["n"]), pct(A["baseline_ok"], A["n"])),
        ("final correct", pct(E["final_ok"], E["n"]), pct(A["final_ok"], A["n"])),
        (
            "wrong baselines detected",
            pct(E["detected"], E["wrong"]),
            pct(A["detected"], A["wrong"]),
        ),
        ("wrong baselines fixed", pct(E["fixed"], E["wrong"]), pct(A["fixed"], A["wrong"])),
        (
            "false alarms (correct baseline sent a feedback round)",
            str(E["false_alarm"]),
            str(A["false_alarm"]),
        ),
        ("regressions (correct → wrong)", str(E["regressions"]), str(A["regressions"])),
    ]
    for name, e, a in rows:
        print(f"| {name} | {e} | {a} |")


if __name__ == "__main__":
    main()
