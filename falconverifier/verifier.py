from __future__ import annotations

import re

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


_TRUNC_RE = re.compile(r":\s*(ℕ|ℤ|Nat|Int)\b")


def lift_to_rat(prop: str) -> str | None:
    """Rewrite ℕ/ℤ ascriptions to ℚ when the claim uses truncating `/` or `-`.

    Natural-language arithmetic ("50% of 150 is 75") is meant over the rationals; a
    formalizer that writes `(50:ℕ)/100*150 = 75` produces a *spurious* refutation because
    ℕ-division truncates. Returns None when no lift applies.
    """
    if not ("/" in prop or "-" in prop) or not _TRUNC_RE.search(prop):
        return None
    return _TRUNC_RE.sub(":ℚ", prop)


def recheck_refutations_over_rat(
    runner: LeanRunner, form: Formalization, report: VerificationReport
) -> None:
    """Retract refutations that only hold because of ℕ/ℤ truncation.

    A refuted claim is re-checked with every ℕ/ℤ literal lifted to ℚ. If the lifted claim
    is *verified*, the refutation was a translation artifact and the step is marked verified
    (with the lifted proposition); otherwise the original verdict stands.
    """
    lifted: dict[str, str] = {}
    for s in report.steps:
        if s.verdict == Verdict.REFUTED and s.lean_prop:
            q = lift_to_rat(s.lean_prop)
            if q:
                lifted[f"s{s.index}"] = q
    if report.final_answer_verdict == Verdict.REFUTED and form.problem_prop:
        q = lift_to_rat(form.problem_prop)
        if q:
            lifted[PROBLEM_CLAIM_ID] = q
    if not lifted:
        return
    run = runner.check_claims(lifted)
    for s in report.steps:
        cid = f"s{s.index}"
        if cid in lifted and run.outcomes[cid].verdict == Verdict.VERIFIED:
            s.verdict = Verdict.VERIFIED
            s.lean_prop = lifted[cid]
            s.detail = "verified over ℚ (ℕ/ℤ version refuted only by truncation)"
    if PROBLEM_CLAIM_ID in lifted and run.outcomes[PROBLEM_CLAIM_ID].verdict == Verdict.VERIFIED:
        form.problem_prop = lifted[PROBLEM_CLAIM_ID]
        report.final_answer_verdict = Verdict.VERIFIED
        report.final_answer_detail = "verified over ℚ (ℕ/ℤ version refuted only by truncation)"


def ill_formed_errors(report: VerificationReport) -> dict[int | str, str]:
    errs: dict[int | str, str] = {}
    for s in report.steps:
        if s.verdict == Verdict.ILL_FORMED:
            errs[s.index] = f"`{s.lean_prop}` -> {s.detail}"
    if report.final_answer_verdict == Verdict.ILL_FORMED:
        errs["final"] = f"problem_prop -> {report.final_answer_detail}"
    return errs
