"""Render bench/results/*/run_*/results.json into docs/BENCHMARK.md (+ SVG bar chart).

Usage:  python bench/report.py [results_dir ...]
Default: latest run in every bench/results/* sub-directory.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "bench" / "results"
DOCS = ROOT / "docs"

KEYS = [
    ("n", "problems"),
    ("baseline_accuracy", "baseline acc"),
    ("verified_accuracy", "verified acc"),
    ("abs_gain", "abs gain"),
    ("rel_error_reduction", "rel. error ↓"),
    ("wrong_baseline", "wrong (baseline)"),
    ("wrong_detected_by_lean", "caught by Lean"),
    ("detection_recall", "detection recall"),
    ("fixed_after_feedback", "fixed after feedback"),
    ("fix_rate", "fix rate"),
    ("false_alarms_on_correct", "false alarms"),
    ("false_alarm_rate", "false-alarm rate"),
    ("regressions", "regressions"),
    ("assured_and_correct", "assured ∧ correct"),
    ("mean_rounds", "mean rounds"),
    ("mean_latency_s", "mean latency (s)"),
]
PCT = {
    "baseline_accuracy",
    "verified_accuracy",
    "abs_gain",
    "rel_error_reduction",
    "detection_recall",
    "fix_rate",
    "false_alarm_rate",
}


def fmt(k: str, v) -> str:
    if v is None:
        return "–"
    if k in PCT:
        return f"{100 * v:.1f}%"
    return str(v)


def latest_runs() -> list[Path]:
    out = []
    if RESULTS.exists():
        for sub in sorted(RESULTS.iterdir()):
            runs = sorted(sub.glob("run_*/results.json"))
            if runs:
                out.append(runs[-1])
    return out


def svg_chart(rows: list[tuple[str, float, float]]) -> str:
    """Grouped bars: baseline vs verified accuracy per slice."""
    h, pad, bw = 260, 48, 46
    w = max(640, 2 * pad + 120 * len(rows))
    gap = (w - 2 * pad) / max(len(rows), 1)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        'font-family="Inter,Segoe UI,sans-serif" font-size="12">',
        f'<rect width="{w}" height="{h}" fill="#0f172a" rx="8"/>',
    ]
    for pct in (0, 25, 50, 75, 100):
        y = h - pad - (h - 2 * pad) * pct / 100
        parts.append(
            f'<line x1="{pad}" x2="{w - pad}" y1="{y:.1f}" y2="{y:.1f}" stroke="#334155"/>'
        )
        parts.append(
            f'<text x="{pad - 8}" y="{y + 4:.1f}" fill="#94a3b8" text-anchor="end">{pct}%</text>'
        )
    for i, (label, base, ver) in enumerate(rows):
        cx = pad + gap * (i + 0.5)
        for j, (val, color) in enumerate(((base, "#64748b"), (ver, "#22c55e"))):
            bh = (h - 2 * pad) * val
            x = cx - bw + j * (bw + 4)
            y = h - pad - bh
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{bh:.1f}" fill="{color}" rx="3"/>'
            )
            parts.append(
                f'<text x="{x + bw / 2:.1f}" y="{y - 5:.1f}" fill="#e2e8f0" text-anchor="middle">{100 * val:.0f}%</text>'
            )
        parts.append(
            f'<text x="{cx:.1f}" y="{h - pad + 18}" fill="#e2e8f0" text-anchor="middle">{label}</text>'
        )
    parts.append(
        f'<rect x="{w - 200}" y="14" width="12" height="12" fill="#64748b"/>'
        f'<text x="{w - 182}" y="24" fill="#e2e8f0">Falcon baseline</text>'
    )
    parts.append(
        f'<rect x="{w - 200}" y="34" width="12" height="12" fill="#22c55e"/>'
        f'<text x="{w - 182}" y="44" fill="#e2e8f0">Falcon + Lean verifier</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def cot_coverage(run_dir: Path) -> list[str]:
    """Step- and round-level verdict distribution over every trace in a run directory."""
    steps: Counter[str] = Counter()
    finals: Counter[str] = Counter()
    rounds = 0
    for tp in run_dir.glob("*.json"):
        if tp.name == "results.json":
            continue
        trace = json.loads(tp.read_text())
        for r in trace.get("rounds", []):
            rounds += 1
            steps.update(s["verdict"] for s in r["report"]["steps"])
            finals[r["report"]["final_answer_verdict"]] += 1
    n_steps = sum(steps.values())
    if not rounds or not n_steps:
        return []
    order = ("verified", "refuted", "unknown", "ill_formed", "unverified_premise", "skipped")
    decided = steps["verified"] + steps["refuted"]
    decided_final = finals["verified"] + finals["refuted"]
    return [
        f"**CoT verifiability** ({rounds} rounds, {n_steps} reasoning steps): Lean decided "
        f"{decided / n_steps:.1%} of steps and {decided_final / rounds:.1%} of final answers.",
        "",
        "| verdict | steps | final answers |",
        "|---|---|---|",
        *(
            f"| {v} | {steps[v]} ({steps[v] / n_steps:.1%}) | {finals[v]} ({finals[v] / rounds:.1%}) |"
            for v in order
            if steps[v] or finals[v]
        ),
        "",
    ]


def main(paths: list[str]) -> None:
    runs = [Path(p) for p in paths] if paths else latest_runs()
    DOCS.mkdir(exist_ok=True)
    md = [
        "# Benchmark results",
        "",
        "Generated by `python bench/report.py` from `bench/results/*/run_*/results.json`.",
        "",
    ]
    chart_rows: list[tuple[str, float, float]] = []
    for rp in runs:
        d = json.loads(rp.read_text())
        name = rp.parent.parent.name
        md += [
            f"## {name} — `{rp.parent.name}`",
            "",
            f"student `{d['student_model']}` · formalizer `{d['formalizer_model']}` · "
            f"max rounds {d['max_rounds']} · wall {d['wall_time_s']:.0f}s · errors {d['errors']}",
            "",
        ]
        slices = [
            s
            for s in ("all", "math", "logic", "hard", "fragment", "eastern-digits")
            if s in d["summary"]
            and (s not in {"hard"} or d["summary"][s]["n"] != d["summary"]["all"]["n"])
        ]
        md.append("| metric | " + " | ".join(slices) + " |")
        md.append("|---|" + "---|" * len(slices))
        for k, label in KEYS:
            md.append(
                f"| {label} | " + " | ".join(fmt(k, d["summary"][s].get(k)) for s in slices) + " |"
            )
        md.append("")
        md += cot_coverage(rp.parent)
        for s in ("math", "logic"):
            if s in d["summary"]:
                sm = d["summary"][s]
                chart_rows.append(
                    (
                        f"{name.replace('falcon_formalizer', 'F').replace('_', ' ')} {s}",
                        sm["baseline_accuracy"],
                        sm["verified_accuracy"],
                    )
                )
        wrong = [r for r in d["rows"] if "error" not in r and not r["baseline_correct"]]
        if wrong:
            md += [
                "<details><summary>Problems Falcon got wrong at baseline</summary>",
                "",
                "| id | expected | baseline | final | Lean flagged r1 | status |",
                "|---|---|---|---|---|---|",
            ]
            for r in wrong:
                md.append(
                    f"| {r['id']} | {r['expected']} | {r['baseline_answer']} | {r['final_answer']} | "
                    f"{'yes' if r['r1_flagged'] else 'no'} | {r['status']} |"
                )
            md += ["", "</details>", ""]
    if chart_rows:
        (DOCS / "benchmark.svg").write_text(svg_chart(chart_rows))
        md.insert(3, "![baseline vs verified accuracy](benchmark.svg)\n")
    (DOCS / "BENCHMARK.md").write_text("\n".join(md))
    print(f"wrote {DOCS / 'BENCHMARK.md'} ({len(runs)} runs)")


if __name__ == "__main__":
    main(sys.argv[1:])
