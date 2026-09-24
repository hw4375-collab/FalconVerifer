from __future__ import annotations

from .schemas import Formalization, Verdict, VerificationReport


def build_feedback(report: VerificationReport, form: Formalization) -> str:
    """Turn Lean verdicts into a concise teaching message for the student model.

    Only *refuted* claims are asserted as wrong (they are machine-proved false). Unknown /
    ill-formed steps are mentioned softly so the student re-examines them without being
    told they are wrong.
    """
    lines: list[str] = []
    refuted = report.refuted
    if refuted:
        lines.append("The proof assistant PROVED that the following steps are FALSE:")
        for s in refuted:
            lines.append(f'  - Step {s.index}: "{s.step_text}"')
            lines.append(f"      formal claim checked: {s.lean_prop}")
            lines.append("      Lean 4 verdict: the negation of this claim is a theorem.")
    if report.final_answer_verdict == Verdict.REFUTED and report.final_answer_detail.startswith(
        "inconsistent final answer"
    ):
        lines.append(
            "Your FINAL ANSWER does not match what your own steps derive. Lean 4 verified "
            f"`{form.problem_prop}` — the number after FINAL ANSWER must be the result of that "
            "computation, so re-read your steps and state the value they actually produce."
        )
    elif report.final_answer_verdict == Verdict.REFUTED:
        lines.append(
            "The proof assistant PROVED that your FINAL ANSWER is inconsistent with the "
            f"problem data. Formal check: `{form.problem_prop}` is FALSE."
        )
    if report.verified:
        ok = ", ".join(str(s.index) for s in report.verified)
        lines.append(f"Steps verified correct by Lean 4: {ok}.")
    if report.final_answer_verdict == Verdict.VERIFIED and not refuted:
        lines.append("Your final answer was verified against the problem data.")
    soft = [s for s in report.steps if s.verdict in (Verdict.UNKNOWN, Verdict.ILL_FORMED)]
    if soft:
        idx = ", ".join(str(s.index) for s in soft)
        lines.append(f"Steps that could not be checked automatically (re-examine them): {idx}.")
    lines.append(
        "Recompute the refuted steps carefully (do the arithmetic digit by digit, or re-derive "
        "the logical inference from the premises) and give a corrected solution."
    )
    return "\n".join(lines)
