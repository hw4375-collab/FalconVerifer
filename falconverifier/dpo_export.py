"""Turn assurance traces into preference data (direction 3: Lean feedback as a training signal).

Every trace in which Lean refuted a round and a later round was fully verified yields one
preference pair::

    prompt   = the original problem (same system prompt the student saw)
    rejected = the Falcon answer Lean refuted (raw text, steps + FINAL ANSWER)
    chosen   = the final answer Lean verified (and, when the trace carries an expected answer,
               that also matches it — so false alarms never produce a "chosen")
    evidence = the refuted Lean claims, their kernel diagnostics and the teaching feedback

The evidence field is what makes this different from ordinary DPO data: each pair is backed by
a Lean proof of ¬P for the rejected reasoning, not by a human or LLM judge.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .arabic import is_arabic
from .bench import answers_match
from .schemas import Verdict

TRACE_SKIP = {"results.json", "latest.json"}


@dataclass
class Evidence:
    refuted_claims: list[dict[str, str]]
    feedback: str
    chosen_claims: list[str]


@dataclass
class PreferencePair:
    prompt: str
    chosen: str
    rejected: str
    evidence: Evidence
    meta: dict[str, str | int | float] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return hashlib.sha1(f"{self.prompt}\n---\n{self.rejected}".encode()).hexdigest()[:16]


def _refuted_claims(report: dict, problem_prop: str | None) -> list[dict[str, str]]:
    out = []
    for s in report.get("steps", []):
        if s.get("verdict") == Verdict.REFUTED.value and s.get("lean_prop"):
            out.append(
                {
                    "step": str(s.get("index", "")),
                    "text": s.get("step_text") or "",
                    "lean_prop": s["lean_prop"],
                    "detail": s.get("detail") or "",
                }
            )
    if report.get("final_answer_verdict") == Verdict.REFUTED.value:
        out.append(
            {
                "step": "final",
                "text": "",
                "lean_prop": problem_prop or "",
                "detail": report.get("final_answer_detail") or "",
            }
        )
    return out


def _verified_claims(report: dict) -> list[str]:
    return [
        s["lean_prop"]
        for s in report.get("steps", [])
        if s.get("verdict") == Verdict.VERIFIED.value and s.get("lean_prop")
    ]


def _round_verified(report: dict) -> bool:
    bad = {Verdict.REFUTED.value, Verdict.ILL_FORMED.value}
    return report.get("final_answer_verdict") == Verdict.VERIFIED.value and not any(
        s.get("verdict") in bad for s in report.get("steps", [])
    )


def pairs_from_trace(
    trace: dict, source: str = "", require_expected: bool = True
) -> list[PreferencePair]:
    """All (rejected, chosen) pairs in one trace; empty when nothing verified at the end.

    With ``require_expected`` (default) traces without a gold answer are skipped: a Lean
    ``verified`` on the chosen round proves the *formalized* claims, and only the gold answer
    rules out an unfaithful formalization having been verified.
    """
    rounds = trace.get("rounds", [])
    if not rounds:
        return []
    expected = trace.get("expected_answer")
    if require_expected and not expected:
        return []
    chosen_round = None
    for r in reversed(rounds):
        if _round_verified(r["report"]):
            chosen_round = r
            break
    if chosen_round is None:
        return []
    chosen_text = chosen_round["answer"]["raw"]
    if expected and not answers_match(chosen_round["answer"].get("final_answer"), expected):
        return []
    pairs = []
    for r in rounds:
        if r is chosen_round:
            break
        refuted = _refuted_claims(r["report"], r.get("formalization", {}).get("problem_prop"))
        if not refuted:
            continue
        rejected_text = r["answer"]["raw"]
        if rejected_text.strip() == chosen_text.strip():
            continue
        pairs.append(
            PreferencePair(
                prompt=trace["problem"],
                chosen=chosen_text,
                rejected=rejected_text,
                evidence=Evidence(
                    refuted_claims=refuted,
                    feedback=r.get("feedback") or "",
                    chosen_claims=_verified_claims(chosen_round["report"]),
                ),
                meta={
                    "source": source,
                    "lang": "ar" if is_arabic(trace["problem"]) else "en",
                    "student_model": trace.get("student_model", ""),
                    "formalizer_model": trace.get("formalizer_model", ""),
                    "rejected_round": int(r["round_index"]),
                    "chosen_round": int(chosen_round["round_index"]),
                    "expected_answer": expected or "",
                },
            )
        )
    return pairs


def iter_trace_files(roots: list[Path]):
    for root in roots:
        if root.is_file():
            yield root
            continue
        for p in sorted(root.rglob("*.json")):
            if p.name not in TRACE_SKIP:
                yield p


def export(roots: list[Path], out: Path, require_expected: bool = True) -> dict[str, int]:
    seen: set[str] = set()
    stats = {"traces": 0, "pairs": 0, "duplicates": 0, "ar": 0, "en": 0}
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for path in iter_trace_files(roots):
            try:
                trace = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if not isinstance(trace, dict) or "rounds" not in trace or "problem" not in trace:
                continue
            stats["traces"] += 1
            for pair in pairs_from_trace(trace, str(path), require_expected):
                if pair.key in seen:
                    stats["duplicates"] += 1
                    continue
                seen.add(pair.key)
                stats["pairs"] += 1
                stats[str(pair.meta["lang"])] += 1
                row = asdict(pair)
                row["id"] = pair.key
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return stats
