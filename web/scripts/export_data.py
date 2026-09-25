"""Export committed benchmark results and the curated demo traces as static JSON for the web app.

Reads bench/results/<arm>/run_*/ (latest run per arm, the same choice as /api/bench/runs) and
writes web/public/data/{bench.json, examples.json, traces/*.json}. Run: python web/scripts/export_data.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = REPO / "bench" / "results"
OUT = REPO / "web" / "public" / "data"

ARM_ORDER = [
    "falcon3b_arabic",
    "falcon3b_arabic_scale",
    "l20_ar",
    "daily_ar",
    "falcon7b_arabic",
    "falcon3b_formalizer",
    "l20_en",
    "falcon3b_v2",
    "falcon3b_formalizer_hard",
    "falcon_formalizer",
    "falcon_formalizer_hard",
]
SUMMARY_KEYS = [
    "n",
    "baseline_accuracy",
    "verified_accuracy",
    "abs_gain",
    "wrong_baseline",
    "wrong_detected_by_lean",
    "detection_recall",
    "false_alarms_on_correct",
    "false_alarm_rate",
    "fixed_after_feedback",
    "fix_rate",
    "regressions",
    "assured_final_answers",
    "assured_and_correct",
    "mean_rounds",
    "mean_latency_s",
]

# The demo's recorded runs: real traces where the Falcon student was wrong in round 1, Lean caught
# it and the loop ended verified. Glosses are English translations of the Arabic questions.
EXAMPLES = [
    {
        "key": "dates",
        "src": "falcon3b_arabic/run_20260925T055916Z/armath-019",
        "kind": "arith",
        "title": {"en": "Hamdan's dates", "ar": "تمر حمدان"},
        "gloss": "Hamdan buys 59 boxes of 41 dates each, then gives 128 dates to his friends. How many dates does Hamdan have left?",
    },
    {
        "key": "discount",
        "src": "falcon3b_arabic/run_20260924T215756Z/armath-048",
        "kind": "arith",
        "title": {"en": "Two discounts", "ar": "خصمان متتاليان"},
        "gloss": "A phone costs 800 dirhams. It is discounted by 10%, then the new price by another 20%. What is the final price in dirhams?",
    },
    {
        "key": "taller",
        "src": "falcon3b_arabic/run_20260924T225108Z/arlogic-016",
        "kind": "logic",
        "title": {"en": "Who is taller?", "ar": "من الأطول؟"},
        "gloss": "Omar is taller than Yusuf, and Yusuf is taller than Khalid. Must Omar be taller than Khalid? Answer yes or no.",
    },
    {
        "key": "handshakes",
        "src": "falcon3b_arabic/run_20260925T055916Z/arlogic-028",
        "kind": "logic",
        "title": {"en": "Eight guests shake hands", "ar": "مصافحة ثمانية ضيوف"},
        "gloss": "At a party of 8 guests, each guest shook hands with exactly 3 of the others. Is that possible? Answer yes or no.",
    },
    {
        "key": "order",
        "src": "falcon3b_arabic/run_20260925T055916Z/armath-050",
        "kind": "arith",
        "title": {"en": "Order of operations", "ar": "ترتيب العمليات"},
        "gloss": "Evaluate 36 + 9 × 8 − 3² following the order of operations.",
    },
    {
        "key": "pens",
        "src": "falcon3b_arabic/run_20260925T055916Z/armath-018",
        "kind": "arith",
        "title": {"en": "Omar's pens", "ar": "أقلام عمر"},
        "gloss": "Omar buys 86 boxes of 40 pens each, then gives 65 pens to his friends. How many pens does Omar have left?",
    },
    {
        "key": "friends",
        "src": "falcon3b_arabic/run_20260925T055916Z/arlogic-031",
        "kind": "logic",
        "title": {"en": "Four friends", "ar": "أربعة أصدقاء"},
        "gloss": "Four students; each says he has four friends among them. Must one of them be lying? Answer yes or no.",
    },
    {
        "key": "trip",
        "src": "falcon_formalizer/run_20260924T195449Z/math-031",
        "kind": "arith",
        "title": {"en": "A road trip", "ar": "رحلة بالسيارة"},
        "gloss": None,
    },
    {
        "key": "five",
        "src": "falcon3b_arabic/run_20260925T055916Z/arlogic-025",
        "kind": "logic",
        "title": {"en": "Five classmates", "ar": "خمسة زملاء"},
        "gloss": "Five students sit in class; each says three of the other four are his friends. Must one of them be lying? Answer yes or no.",
    },
]


def latest_run(arm_dir: Path) -> Path | None:
    runs = sorted(arm_dir.glob("run_*/results.json"))
    return runs[-1].parent if runs else None


def problems_of(dataset: str) -> dict[str, str]:
    path = REPO / dataset
    out: dict[str, str] = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                out[item["id"]] = item["problem"]
    return out


def cot_coverage(run_dir: Path) -> dict:
    """Same counting as bench/report.py: every round of every trace in the run."""
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
    return {"rounds": rounds, "steps": dict(steps), "finals": dict(finals)}


def short(value, limit: int = 90) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def export_bench() -> dict:
    arms = []
    names = [a for a in ARM_ORDER if (RESULTS / a).is_dir()]
    names += sorted(p.name for p in RESULTS.iterdir() if p.is_dir() and p.name not in names)
    for name in names:
        run_dir = latest_run(RESULTS / name)
        if run_dir is None:
            continue
        data = json.loads((run_dir / "results.json").read_text())
        problems = problems_of(data.get("dataset", ""))
        rows = []
        for r in data.get("rows", []):
            if r.get("error"):
                continue
            rows.append(
                {
                    "id": r["id"],
                    "tags": r.get("tags", []),
                    "expected": r.get("expected"),
                    "base": short(r.get("baseline_answer")),
                    "baseOk": bool(r.get("baseline_correct")),
                    "final": short(r.get("final_answer")),
                    "finalOk": bool(r.get("final_correct")),
                    "rounds": r.get("rounds"),
                    "status": r.get("status"),
                    "flagged": bool(r.get("r1_flagged")),
                    "latency": r.get("latency_s"),
                }
            )
        summary = {
            slice_: {k: s.get(k) for k in SUMMARY_KEYS}
            for slice_, s in (data.get("summary") or {}).items()
            if s
        }
        arms.append(
            {
                "key": name,
                "run": run_dir.name,
                "dataset": data.get("dataset"),
                "lang": "ar" if "_ar" in str(data.get("dataset", "")) else "en",
                "student": data.get("student_model"),
                "formalizer": data.get("formalizer_model"),
                "maxRounds": data.get("max_rounds"),
                "wallTime": data.get("wall_time_s"),
                "summary": summary,
                "cot": cot_coverage(run_dir),
                "rows": rows,
                "problems": {r["id"]: problems.get(r["id"], "") for r in rows},
            }
        )
    return {"arms": arms}


def slim_trace(trace: dict) -> dict:
    rounds = []
    for r in trace["rounds"]:
        a, f, rep = r["answer"], r.get("formalization") or {}, r.get("report") or {}
        lean = "\n".join(
            line
            for line in (rep.get("lean_file") or "").splitlines()
            if line.startswith(("import ", "theorem "))
        )
        rounds.append(
            {
                "round": r["round_index"],
                "answer": {
                    "raw": a["raw"],
                    "final": a.get("final_answer"),
                    "steps": a.get("steps", []),
                    "latency": round(a.get("latency_s", 0.0), 2),
                },
                "formalization": {
                    "problemProp": f.get("problem_prop"),
                    "problemNote": f.get("problem_note", ""),
                    "steps": [
                        {
                            "index": s["index"],
                            "leanProp": s.get("lean_prop"),
                            "note": s.get("note", ""),
                        }
                        for s in f.get("steps", [])
                    ],
                },
                "report": {
                    "steps": [
                        {
                            "index": s["index"],
                            "verdict": s["verdict"],
                            "leanProp": s.get("lean_prop"),
                            "text": s.get("step_text", ""),
                            "detail": s.get("detail", ""),
                        }
                        for s in rep.get("steps", [])
                    ],
                    "final": rep.get("final_answer_verdict"),
                    "finalDetail": rep.get("final_answer_detail", ""),
                    "leanLatency": round(rep.get("lean_latency_s", 0.0), 2),
                    "lean": lean,
                },
                "feedback": r.get("feedback"),
            }
        )
    return {
        "problem": trace["problem"],
        "expected": trace.get("expected_answer"),
        "student": trace["student_model"],
        "formalizer": trace["formalizer_model"],
        "final": trace.get("final_answer"),
        "status": trace["status"],
        "assurance": trace.get("assurance_score"),
        "latency": trace.get("total_latency_s"),
        "rounds": rounds,
    }


def export_examples() -> list[dict]:
    (OUT / "traces").mkdir(parents=True, exist_ok=True)
    out = []
    for ex in EXAMPLES:
        arm, run, pid = ex["src"].split("/")
        trace = json.loads((RESULTS / arm / run / f"{pid}.json").read_text())
        slim = slim_trace(trace)
        (OUT / "traces" / f"{ex['key']}.json").write_text(
            json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
        )
        out.append(
            {
                "key": ex["key"],
                "kind": ex["kind"],
                "title": ex["title"],
                "question": trace["problem"],
                "gloss": ex["gloss"],
                "student": trace["student_model"],
                "rounds": len(trace["rounds"]),
                "latency": trace["total_latency_s"],
                "base": trace["rounds"][0]["answer"].get("final_answer"),
                "final": trace.get("final_answer"),
                "source": {"arm": arm, "run": run, "id": pid},
            }
        )
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    bench = export_bench()
    (OUT / "bench.json").write_text(json.dumps(bench, ensure_ascii=False, separators=(",", ":")))
    examples = export_examples()
    (OUT / "examples.json").write_text(
        json.dumps({"examples": examples}, ensure_ascii=False, separators=(",", ":"))
    )
    print(f"bench: {len(bench['arms'])} arms, examples: {len(examples)} -> {OUT}")


if __name__ == "__main__":
    main()
