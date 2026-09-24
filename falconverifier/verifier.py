from __future__ import annotations

from .lean_runner import LeanRunner
from .schemas import (
    Formalization,
    ReasoningStep,
    StepResult,
    Verdict,
    VerificationReport,
)

PROBLEM_CLAIM_ID = "final"


def verify(
    runner: LeanRunner, steps: list[ReasoningStep], form: Formalization
) -> VerificationReport:
    """Check every formalized step and the final-answer claim in one Lean compilation."""
    claims: dict[str, str] = {}
    for fs in form.steps:
        if fs.lean_prop:
            claims[f"s{fs.index}"] = fs.lean_prop
    if form.problem_prop:
        claims[PROBLEM_CLAIM_ID] = form.problem_prop

    run = runner.check_claims(claims)
    text_by_index = {s.index: s.text for s in steps}

    results: list[StepResult] = []
    for fs in form.steps:
        cid = f"s{fs.index}"
        if fs.lean_prop is None:
            results.append(
                StepResult(
                    index=fs.index,
                    verdict=Verdict.SKIPPED,
                    lean_prop=None,
                    step_text=text_by_index.get(fs.index, ""),
                    detail=fs.note,
                )
            )
            continue
        out = run.outcomes[cid]
        results.append(
            StepResult(
                index=fs.index,
                verdict=out.verdict,
                lean_prop=fs.lean_prop,
                step_text=text_by_index.get(fs.index, ""),
                detail=out.detail,
            )
        )

    if form.problem_prop:
        fo = run.outcomes[PROBLEM_CLAIM_ID]
        final_verdict, final_detail = fo.verdict, fo.detail
    else:
        final_verdict, final_detail = Verdict.SKIPPED, "final answer not formalizable"

    return VerificationReport(
        steps=results,
        final_answer_verdict=final_verdict,
        final_answer_detail=final_detail,
        lean_file=run.source,
        lean_latency_s=run.latency_s,
        diagnostics=run.diagnostics,
    )


def ill_formed_errors(report: VerificationReport) -> dict[int | str, str]:
    errs: dict[int | str, str] = {}
    for s in report.steps:
        if s.verdict == Verdict.ILL_FORMED:
            errs[s.index] = f"`{s.lean_prop}` -> {s.detail}"
    if report.final_answer_verdict == Verdict.ILL_FORMED:
        errs["final"] = f"problem_prop -> {report.final_answer_detail}"
    return errs
