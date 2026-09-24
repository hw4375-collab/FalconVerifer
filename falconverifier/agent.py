from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .arabic import is_arabic
from .config import Settings
from .feedback import build_feedback
from .formalizer import Formalizer, degenerate_inference
from .lean_runner import LeanRunner
from .llm import ChatModel, OpenAICompatibleClient
from .schemas import Formalization, Round, Trace, Verdict, VerificationReport
from .student import Student, yes_no_polarity
from .verifier import (
    check_final_grounding,
    ill_formed_errors,
    literals_grounded,
    recheck_refutations_over_rat,
    verify,
)

log = logging.getLogger(__name__)

EventCallback = Callable[[str, dict[str, Any]], None]


def assurance_score(report: VerificationReport | None) -> float:
    if report is None:
        return 0.0
    if report.has_errors:
        return 0.1
    checkable = [s for s in report.steps if s.verdict != Verdict.SKIPPED]
    step_part = (len(report.verified) / len(checkable)) if checkable else 0.5
    final_part = {
        Verdict.VERIFIED: 1.0,
        Verdict.UNKNOWN: 0.4,
        Verdict.ILL_FORMED: 0.3,
        Verdict.SKIPPED: 0.4,
        Verdict.REFUTED: 0.0,
    }[report.final_answer_verdict]
    return round(0.5 * step_part + 0.5 * final_part, 3)


def status_of(report: VerificationReport | None) -> str:
    if report is None:
        return "unknown"
    if report.has_errors:
        return "refuted"
    if report.final_answer_verdict == Verdict.VERIFIED:
        return "verified"
    return "unknown"


class VerifyAndTeachAgent:
    """Falcon answers -> formalize to Lean 4 -> Lean checks -> teach Falcon -> repeat."""

    def __init__(
        self,
        settings: Settings,
        student_model: ChatModel | None = None,
        formalizer_model: ChatModel | None = None,
        runner: LeanRunner | None = None,
        on_event: EventCallback | None = None,
        audit_refutations: bool = True,
    ):
        self.settings = settings
        self.audit_refutations = audit_refutations
        self.student = Student(student_model or OpenAICompatibleClient(settings.student))
        self.formalizer = Formalizer(
            formalizer_model or OpenAICompatibleClient(settings.formalizer)
        )
        self.runner = runner or LeanRunner(settings.lean_project_dir, settings.lean_timeout)
        self.on_event = on_event or (lambda kind, payload: None)

    def _emit(self, kind: str, **payload: Any) -> None:
        try:
            self.on_event(kind, payload)
        except Exception:  # never let UI callbacks break the loop
            log.exception("event callback failed")

    def _audit(
        self,
        problem: str,
        form: Formalization,
        report: VerificationReport,
        final_answer: str | None = None,
    ) -> None:
        """Drop refutations whose Lean translation does not match the step's meaning.

        A refutation is a strong claim ("Lean proved you wrong"), so it must survive a
        faithfulness check; otherwise it is downgraded to `unknown`.
        """
        grammar_steps = {fs.index for fs in form.steps if fs.note.startswith("pregroup:")}
        for s in report.steps:
            if s.verdict != Verdict.REFUTED or not s.lean_prop:
                continue
            if s.index in grammar_steps:
                continue  # deterministic translation with a derivation certificate
            if literals_grounded(s.lean_prop, s.step_text, problem) and "¬" not in s.lean_prop:
                continue  # pure arithmetic over the student's own numbers: no LLM opinion needed
            ok, reason = self.formalizer.audit(problem, s.step_text, s.lean_prop)
            if not ok:
                s.verdict = Verdict.UNKNOWN
                s.detail = f"refutation discarded (unfaithful translation): {reason}"
                self._emit("audit_discard", step=s.index, reason=reason)
        if (
            report.final_answer_verdict == Verdict.REFUTED
            and form.problem_prop
            and form.raw != "pregroup"
            and not form.problem_note.startswith("pregroup:")
            and not report.final_answer_detail.startswith("inconsistent final answer")
            and not literals_grounded(form.problem_prop, problem, final_answer or "")
        ):
            if final_answer is not None and yes_no_polarity(final_answer) is not None:
                ok, reason = self.formalizer.audit_yes_no(problem, final_answer, form.problem_prop)
            else:
                ok, reason = self.formalizer.audit(
                    problem,
                    f"The student's FINAL ANSWER to the question is: {final_answer!r}",
                    form.problem_prop,
                )
            if not ok:
                report.final_answer_verdict = Verdict.UNKNOWN
                report.final_answer_detail = f"refutation discarded: {reason}"
                self._emit("audit_discard", step="final", reason=reason)
        elif (
            report.final_answer_verdict == Verdict.VERIFIED
            and form.problem_prop
            and form.raw != "pregroup"
            and not form.problem_note.startswith("pregroup:")
            and yes_no_polarity(final_answer) is not None
            and degenerate_inference(form.problem_prop)
        ):
            report.final_answer_verdict = Verdict.UNKNOWN
            report.final_answer_detail = (
                "verification discarded: degenerate inference (conclusion is a premise)"
            )
            self._emit("audit_discard", step="final", reason=report.final_answer_detail)

    def run(
        self, problem: str, expected_answer: str | None = None, max_rounds: int | None = None
    ) -> Trace:
        max_rounds = max_rounds or self.settings.max_rounds
        t_start = time.time()
        rounds: list[Round] = []
        history: list[dict[str, str]] = [{"role": "user", "content": problem}]
        last_report: VerificationReport | None = None
        final_answer: str | None = None

        for r in range(max_rounds):
            self._emit("round_start", round=r + 1, max_rounds=max_rounds)
            answer = self.student.solve(problem, history)
            history.append({"role": "assistant", "content": answer.raw})
            final_answer = answer.final_answer
            self._emit("student_answer", round=r + 1, answer=answer.model_dump())

            form, fmsgs = self.formalizer.formalize(problem, answer.steps, answer.final_answer)
            self._emit("formalized", round=r + 1, formalization=form.model_dump())
            report = verify(self.runner, answer.steps, form)

            errs = ill_formed_errors(report)
            if errs:  # one repair attempt for translation errors
                self._emit("repair", round=r + 1, errors={str(k): v for k, v in errs.items()})
                form2, _ = self.formalizer.repair(fmsgs, errs, answer.steps, answer.final_answer)
                report2 = verify(self.runner, answer.steps, form2)
                if len(ill_formed_errors(report2)) < len(errs):
                    form, report = form2, report2
            if report.has_errors:
                recheck_refutations_over_rat(self.runner, form, report)
                self._emit("rat_recheck", round=r + 1)
            check_final_grounding(answer.final_answer, form, report)
            if self.audit_refutations:
                self._audit(problem, form, report, answer.final_answer)
            self._emit("verified", round=r + 1, report=report.model_dump())
            last_report = report

            missing_final = answer.final_answer is None
            done = not report.has_errors and not missing_final
            feedback = (
                None
                if done or r == max_rounds - 1
                else build_feedback(
                    report, form, arabic=is_arabic(problem), missing_final=missing_final
                )
            )
            rounds.append(
                Round(
                    round_index=r + 1,
                    answer=answer,
                    formalization=form,
                    report=report,
                    feedback=feedback,
                )
            )
            if done:
                break
            if feedback:
                self._emit("feedback", round=r + 1, feedback=feedback)
                history.append(
                    {
                        "role": "user",
                        "content": Student.revision_message(feedback, arabic=is_arabic(problem)),
                    }
                )

        status = status_of(last_report)
        if status == "refuted" and len(rounds) == max_rounds:
            status = "max_rounds"
        trace = Trace(
            problem=problem,
            expected_answer=expected_answer,
            student_model=self.student.model.model,
            formalizer_model=self.formalizer.model.model,
            rounds=rounds,
            final_answer=final_answer,
            status=status,
            assurance_score=assurance_score(last_report),
            total_latency_s=round(time.time() - t_start, 2),
        )
        self._emit("done", trace=trace.model_dump())
        return trace

    def save_trace(self, trace: Trace, directory: Path | None = None) -> Path:
        directory = directory or self.settings.runs_dir
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = directory / f"trace_{stamp}.json"
        path.write_text(json.dumps(trace.model_dump(), ensure_ascii=False, indent=2))
        return path
