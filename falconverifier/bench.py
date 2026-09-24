from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from .agent import VerifyAndTeachAgent
from .arabic import normalize_digits
from .config import Settings
from .schemas import Trace, Verdict

log = logging.getLogger(__name__)
console = Console()


# --- answer normalisation ------------------------------------------------------------

_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?:/\d+)?")


def _to_number(s: str) -> Fraction | None:
    s = s.replace(",", "").replace("$", "").replace("%", "").strip()
    m = _NUM_RE.search(s)
    if not m:
        return None
    tok = m.group(0).replace(",", "")
    try:
        if "/" in tok:
            a, b = tok.split("/")
            return Fraction(int(a), int(b))
        return Fraction(tok)
    except (ValueError, ZeroDivisionError):
        return None


def answers_match(pred: str | None, expected: str) -> bool:
    if pred is None:
        return False
    p, e = normalize_digits(pred).strip().lower(), normalize_digits(expected).strip().lower()
    syn = {
        "yes": {"yes", "true", "valid", "نعم", "صحيح", "صح"},
        "no": {"no", "false", "invalid", "لا", "خطأ", "خاطئ"},
    }
    if e in syn["yes"] | syn["no"]:
        p = re.sub(r"(?:غير|ليس)\s+صحيح\w*", "خطأ", p)
        p_word = re.sub(r"[^a-z\u0621-\u064a]", " ", p).split()
        key = "yes" if e in syn["yes"] else "no"
        other = "no" if key == "yes" else "yes"
        return any(w in syn[key] for w in p_word[:3]) and not any(
            w in syn[other] for w in p_word[:3]
        )
    if "=" in p:  # "(a+b)/2 = 51" -> grade the stated result, not the expression
        p = p.rsplit("=", 1)[1]
    pn, en = _to_number(p), _to_number(e)
    if pn is not None and en is not None:
        return pn == en
    p_key, e_key = (re.sub(r"[^a-z0-9\u0621-\u064a]", "", x) for x in (p, e))
    return bool(e_key) and p_key == e_key


# --- benchmark -----------------------------------------------------------------------


def load_problems(path: Path, limit: int | None = None, tag: str | None = None) -> list[dict]:
    items = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        d = json.loads(line)
        if tag and tag not in d.get("tags", []):
            continue
        items.append(d)
    return items[:limit] if limit else items


def evaluate_trace(trace: Trace, expected: str) -> dict[str, Any]:
    r1 = trace.rounds[0]
    baseline_answer = r1.answer.final_answer
    baseline_correct = answers_match(baseline_answer, expected)
    final_correct = answers_match(trace.final_answer, expected)
    r1_report = r1.report
    r1_flagged = bool(r1_report and r1_report.has_errors)
    r1_refuted_steps = len(r1_report.refuted) if r1_report else 0
    r1_checkable = (
        len([s for s in r1_report.steps if s.verdict != Verdict.SKIPPED]) if r1_report else 0
    )
    r1_verified = len(r1_report.verified) if r1_report else 0
    return {
        "baseline_answer": baseline_answer,
        "baseline_correct": baseline_correct,
        "final_answer": trace.final_answer,
        "final_correct": final_correct,
        "rounds": trace.n_rounds,
        "status": trace.status,
        "assurance": trace.assurance_score,
        "r1_flagged": r1_flagged,
        "r1_refuted_steps": r1_refuted_steps,
        "r1_checkable_steps": r1_checkable,
        "r1_verified_steps": r1_verified,
        "r1_final_verdict": r1_report.final_answer_verdict.value if r1_report else None,
        "latency_s": trace.total_latency_s,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {}
    base = sum(r["baseline_correct"] for r in rows)
    fin = sum(r["final_correct"] for r in rows)
    wrong_base = [r for r in rows if not r["baseline_correct"]]
    right_base = [r for r in rows if r["baseline_correct"]]
    flagged_wrong = sum(r["r1_flagged"] for r in wrong_base)
    flagged_right = sum(r["r1_flagged"] for r in right_base)
    fixed = sum(r["final_correct"] for r in wrong_base)
    broke = sum(not r["final_correct"] for r in right_base)
    # "hallucination" = a machine-refuted step or a refuted final answer in the first answer
    halluc_r1 = sum(
        1 for r in rows if r["r1_refuted_steps"] > 0 or r["r1_final_verdict"] == "refuted"
    )
    return {
        "n": n,
        "baseline_accuracy": round(base / n, 4),
        "verified_accuracy": round(fin / n, 4),
        "abs_gain": round((fin - base) / n, 4),
        "rel_error_reduction": round((fin - base) / (n - base), 4) if n > base else 0.0,
        "wrong_baseline": len(wrong_base),
        "wrong_detected_by_lean": flagged_wrong,
        "detection_recall": round(flagged_wrong / len(wrong_base), 4) if wrong_base else None,
        "false_alarms_on_correct": flagged_right,
        "false_alarm_rate": round(flagged_right / len(right_base), 4) if right_base else None,
        "fixed_after_feedback": fixed,
        "fix_rate": round(fixed / len(wrong_base), 4) if wrong_base else None,
        "regressions": broke,
        "answers_with_refuted_claims_r1": halluc_r1,
        "assured_final_answers": sum(1 for r in rows if r["status"] == "verified"),
        "assured_and_correct": sum(
            1 for r in rows if r["status"] == "verified" and r["final_correct"]
        ),
        "mean_rounds": round(sum(r["rounds"] for r in rows) / n, 2),
        "mean_latency_s": round(sum(r["latency_s"] for r in rows) / n, 1),
    }


def run_benchmark(
    dataset: Path,
    out_dir: Path,
    *,
    limit: int | None = None,
    rounds: int | None = None,
    mode: str = "both",
    workers: int = 4,
    tag: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or Settings.from_env()
    problems = load_problems(dataset, limit, tag)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_dir / f"run_{stamp}"
    run_dir.mkdir()
    console.print(
        f"[bold]Benchmark[/] {len(problems)} problems | student={settings.student.model} "
        f"formalizer={settings.formalizer.model} | workers={workers}"
    )
    max_rounds = 1 if mode == "baseline" else rounds

    def work(item: dict) -> tuple[dict, Trace]:
        agent = VerifyAndTeachAgent(settings)
        trace = agent.run(item["problem"], expected_answer=item["answer"], max_rounds=max_rounds)
        return item, trace

    rows: list[dict[str, Any]] = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, it): it for it in problems}
        for i, fut in enumerate(as_completed(futs), 1):
            item = futs[fut]
            try:
                item, trace = fut.result()
            except Exception as e:  # keep going; record the failure
                log.exception("problem %s failed", item.get("id"))
                rows.append({"id": item.get("id"), "tags": item.get("tags", []), "error": str(e)})
                continue
            ev = evaluate_trace(trace, item["answer"])
            row = {"id": item.get("id"), "tags": item.get("tags", []), "expected": item["answer"]}
            row.update(ev)
            rows.append(row)
            (run_dir / f"{item.get('id', i)}.json").write_text(
                json.dumps(trace.model_dump(), ensure_ascii=False, indent=1)
            )
            mark = "✓" if ev["final_correct"] else "✗"
            b = "✓" if ev["baseline_correct"] else "✗"
            console.print(
                f"[{i}/{len(problems)}] {item.get('id')}: base {b} -> final {mark} "
                f"(rounds={ev['rounds']}, status={ev['status']}, {ev['latency_s']:.0f}s)"
            )

    summary = summarize_by_tag(rows)
    result = {
        "dataset": str(dataset),
        "student_model": settings.student.model,
        "formalizer_model": settings.formalizer.model,
        "max_rounds": max_rounds or settings.max_rounds,
        "wall_time_s": round(time.time() - t0, 1),
        "errors": sum(1 for r in rows if "error" in r),
        "summary": summary,
        "rows": rows,
    }
    (run_dir / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (out_dir / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print_summary(summary)
    console.print(f"results written to {run_dir}")
    return result


def summarize_by_tag(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ok_rows = [r for r in rows if "error" not in r]
    summary = {"all": summarize(ok_rows)}
    for t in sorted({t for r in ok_rows for t in r["tags"]}):
        summary[t] = summarize([r for r in ok_rows if t in r["tags"]])
    return summary


def regrade_run(run_dir: Path) -> dict[str, Any]:
    """Re-apply `answers_match` to a stored run (grader fixes) and rewrite its summary."""
    path = run_dir / "results.json"
    result = json.loads(path.read_text())
    for r in result["rows"]:
        if "error" in r:
            continue
        r["baseline_correct"] = answers_match(r["baseline_answer"], r["expected"])
        r["final_correct"] = answers_match(r["final_answer"], r["expected"])
    result["summary"] = summarize_by_tag(result["rows"])
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (run_dir.parent / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def print_summary(summary: dict[str, Any]) -> None:
    t = Table(title="Falcon baseline vs. Falcon + FalconVerifier")
    t.add_column("slice")
    for c in [
        "n",
        "baseline_accuracy",
        "verified_accuracy",
        "abs_gain",
        "detection_recall",
        "false_alarm_rate",
        "fix_rate",
        "regressions",
        "mean_rounds",
    ]:
        t.add_column(c, justify="right")
    for k, s in summary.items():
        if not s:
            continue
        t.add_row(
            k,
            str(s["n"]),
            f"{s['baseline_accuracy']:.1%}",
            f"{s['verified_accuracy']:.1%}",
            f"{s['abs_gain']:+.1%}",
            "-" if s["detection_recall"] is None else f"{s['detection_recall']:.0%}",
            "-" if s["false_alarm_rate"] is None else f"{s['false_alarm_rate']:.0%}",
            "-" if s["fix_rate"] is None else f"{s['fix_rate']:.0%}",
            str(s["regressions"]),
            str(s["mean_rounds"]),
        )
    console.print(t)
