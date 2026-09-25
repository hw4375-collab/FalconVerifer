from __future__ import annotations

from .formalizer import _outer_negation
from .schemas import Formalization, Verdict, VerificationReport

_EN = {
    "refuted_hdr": "The proof assistant PROVED that the following steps are FALSE:",
    "step": '  - Step {i}: "{t}"',
    "claim": "      formal claim checked: {p}",
    "neg": "      Lean 4 verdict: the negation of this claim is a theorem.",
    "final_inconsistent": (
        "Your FINAL ANSWER does not match what your own steps derive. Lean 4 verified "
        "`{p}` — the number after FINAL ANSWER must be the result of that computation, so "
        "re-read your steps and state the value they actually produce."
    ),
    "final_refuted": (
        "The proof assistant PROVED that your FINAL ANSWER is inconsistent with the "
        "problem data. Formal check: `{p}` is FALSE."
    ),
    "yes_wrong": (
        "You answered YES, but Lean 4 proved that the conclusion does NOT follow from the "
        "premises: there is a situation in which every premise holds and the conclusion fails, "
        "so the correct answer is NO."
    ),
    "no_wrong": (
        "You answered NO, but Lean 4 proved that the conclusion follows necessarily from the "
        "premises: `{p}` is a theorem, so the correct answer is YES. Re-derive the chain of "
        "inferences from the premises."
    ),
    "verified": "Steps verified correct by Lean 4: {ok}.",
    "final_ok": "Your final answer was verified against the problem data.",
    "soft": "Steps that could not be checked automatically (re-examine them): {idx}.",
    "recompute": (
        "Recompute the refuted steps carefully (do the arithmetic digit by digit, or re-derive "
        "the logical inference from the premises) and give a corrected solution."
    ),
    "missing_final": (
        "Your answer has no `FINAL ANSWER: <answer>` line, so it cannot be checked. End your "
        "solution with exactly one such line."
    ),
}

_AR = {
    "refuted_hdr": "أثبت مساعد البرهان (Lean 4) أن الخطوات التالية خاطئة:",
    "step": "  - الخطوة {i}: «{t}»",
    "claim": "      الادعاء الصوري الذي تم فحصه: {p}",
    "neg": "      حكم Lean 4: نفي هذا الادعاء مبرهنة.",
    "final_inconsistent": (
        "الجواب النهائي لا يطابق ما تستنتجه خطواتك. تحقق Lean 4 من `{p}`؛ يجب أن يكون الرقم "
        "بعد «الجواب النهائي» هو نتيجة هذا الحساب، فأعد قراءة خطواتك واذكر القيمة التي تنتجها فعلاً."
    ),
    "final_refuted": (
        "أثبت مساعد البرهان أن جوابك النهائي غير متوافق مع بيانات المسألة. الفحص الصوري: `{p}` خاطئ."
    ),
    "yes_wrong": (
        "أجبت «نعم»، لكن Lean 4 أثبت أن النتيجة لا تلزم من المقدمات: توجد حالة تكون فيها كل "
        "المقدمات صحيحة والنتيجة خاطئة، فالجواب الصحيح هو «لا»."
    ),
    "no_wrong": (
        "أجبت «لا»، لكن Lean 4 أثبت أن النتيجة تلزم بالضرورة من المقدمات: `{p}` مبرهنة، "
        "فالجواب الصحيح هو «نعم». أعد استنتاج سلسلة اللوازم من المقدمات خطوة خطوة."
    ),
    "verified": "الخطوات التي تحقق Lean 4 من صحتها: {ok}.",
    "final_ok": "تم التحقق من جوابك النهائي مقابل بيانات المسألة.",
    "soft": "خطوات لم يمكن فحصها آلياً (أعد النظر فيها): {idx}.",
    "recompute": (
        "أعد حساب الخطوات المرفوضة بعناية (احسب رقماً رقماً، أو أعد استنتاج العلاقة المنطقية من "
        "المقدمات) وقدّم حلاً مصححاً."
    ),
    "missing_final": (
        "جوابك لا يحتوي على سطر «الجواب النهائي: <الجواب>» ولذلك لا يمكن فحصه. اختم حلك "
        "بسطر واحد بهذه الصيغة بالضبط."
    ),
}


def build_feedback(
    report: VerificationReport,
    form: Formalization,
    arabic: bool = False,
    missing_final: bool = False,
    polarity: bool | None = None,
    countermodel: str | None = None,
) -> str:
    """Turn Lean verdicts into a concise teaching message for the student model.

    Only *refuted* claims are asserted as wrong (they are machine-proved false). Unknown /
    ill-formed steps are mentioned softly so the student re-examines them without being
    told they are wrong. The message is written in the language of the problem.
    """
    t = _AR if arabic else _EN
    lines: list[str] = []
    refuted = report.refuted
    if refuted:
        lines.append(t["refuted_hdr"])
        for s in refuted:
            lines.append(t["step"].format(i=s.index, t=s.step_text))
            lines.append(t["claim"].format(p=s.lean_prop))
            lines.append(t["neg"])
    if report.final_answer_verdict == Verdict.REFUTED and report.final_answer_detail.startswith(
        "inconsistent final answer"
    ):
        lines.append(t["final_inconsistent"].format(p=form.problem_prop))
    elif report.final_answer_verdict == Verdict.REFUTED and polarity is True:
        lines.append(t["yes_wrong"])
        if countermodel:
            lines.append(countermodel)
    elif report.final_answer_verdict == Verdict.REFUTED and polarity is False:
        inner = _outer_negation(form.problem_prop or "") or form.problem_prop
        lines.append(t["no_wrong"].format(p=inner))
        if countermodel:
            lines.append(countermodel)
    elif report.final_answer_verdict == Verdict.REFUTED:
        lines.append(t["final_refuted"].format(p=form.problem_prop))
    if report.verified:
        ok = ", ".join(str(s.index) for s in report.verified)
        lines.append(t["verified"].format(ok=ok))
    if report.final_answer_verdict == Verdict.VERIFIED and not refuted:
        lines.append(t["final_ok"])
    if missing_final:
        lines.append(t["missing_final"])
    soft = [s for s in report.steps if s.verdict in (Verdict.UNKNOWN, Verdict.ILL_FORMED)]
    if soft:
        idx = ", ".join(str(s.index) for s in soft)
        lines.append(t["soft"].format(idx=idx))
    lines.append(t["recompute"])
    return "\n".join(lines)
