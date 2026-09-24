from __future__ import annotations

import json

from falconverifier.bench import answers_match, evaluate_trace, summarize
from falconverifier.feedback import build_feedback
from falconverifier.formalizer import Formalizer, _clean_prop
from falconverifier.schemas import (
    Formalization,
    FormalStep,
    ReasoningStep,
    StepResult,
    Verdict,
    VerificationReport,
)
from falconverifier.student import parse_answer


class TestParseAnswer:
    def test_numbered_steps_and_final(self):
        text = "Step 1: 48 * 7 = 336.\nStep 2: 5 * 12 = 60.\nStep 3: 336 - 60 = 276.\nFINAL ANSWER: 276"
        steps, final = parse_answer(text)
        assert [s.index for s in steps] == [1, 2, 3]
        assert steps[2].text == "336 - 60 = 276."
        assert final == "276"

    def test_step_mentioning_final_answer_is_not_the_answer(self):
        text = "Step 4: State the final answer.\nFINAL ANSWER: No"
        steps, final = parse_answer(text)
        assert final == "No"
        assert len(steps) == 1

    def test_markdown_variants(self):
        assert parse_answer("Step 1: x\n**FINAL ANSWER:** $10")[1] == "$10"
        assert parse_answer("Step 1: x\nFINAL ANSWER: **42**.")[1] == "42"
        assert parse_answer("**Step 1:** x\nFinal answer is 7")[1] == "7"

    def test_multiline_step_bodies_are_joined(self):
        text = "Step 1: Identify.\n- A\n- B\nStep 2: Done\nFINAL ANSWER: Yes"
        steps, final = parse_answer(text)
        assert steps[0].text == "Identify. - A - B"
        assert final == "Yes"

    def test_fallback_without_format(self):
        steps, final = parse_answer("First we add.\n\nThen we get 5.\n\nThe final answer is 5")
        assert final == "5"
        assert len(steps) == 2


class TestAnswersMatch:
    def test_numbers(self):
        assert answers_match("276", "276")
        assert answers_match("$10", "10")
        assert answers_match("148.5 km", "148.5")
        assert answers_match("1/2", "0.5")
        assert answers_match("25%", "25")
        assert not answers_match("277", "276")

    def test_yes_no(self):
        assert answers_match("No", "No")
        assert answers_match("No, it does not follow.", "No")
        assert answers_match("Yes.", "yes")
        assert not answers_match("Yes", "No")
        assert not answers_match("", "No")
        assert not answers_match(None, "No")


class TestFormalizerParse:
    def test_clean_prop_strips_theorem_wrappers(self):
        assert _clean_prop("theorem foo : (2:ℕ) + 2 = 4 := by norm_num") == "(2:ℕ) + 2 = 4"
        assert _clean_prop("```lean\n(3:ℚ) / 4 = 0.75\n```") == "(3:ℚ) / 4 = 0.75"
        assert _clean_prop("null") is None
        assert _clean_prop("  ") is None

    def test_parse_json_with_missing_and_skipped_steps(self):
        steps = [ReasoningStep(index=1, text="a"), ReasoningStep(index=2, text="b")]
        raw = json.dumps(
            {
                "problem_prop": "(1:ℕ) = 1",
                "steps": [{"index": 2, "kind": "arith", "lean_prop": "(2:ℕ) = 2", "note": "n"}],
            }
        )
        form = Formalizer._parse("here you go:\n" + raw, steps)
        assert form.problem_prop == "(1:ℕ) = 1"
        assert form.steps[0].kind == "skip" and form.steps[0].lean_prop is None
        assert form.steps[1].lean_prop == "(2:ℕ) = 2"

    def test_parse_garbage_degrades_to_skip(self):
        steps = [ReasoningStep(index=1, text="a")]
        form = Formalizer._parse("I cannot do this", steps)
        assert form.problem_prop is None
        assert all(s.kind == "skip" for s in form.steps)


def _report(verdicts: list[Verdict], final: Verdict) -> VerificationReport:
    return VerificationReport(
        steps=[
            StepResult(index=i + 1, verdict=v, lean_prop=f"p{i}", step_text=f"step {i}")
            for i, v in enumerate(verdicts)
        ],
        final_answer_verdict=final,
        lean_file="",
        lean_latency_s=0.0,
    )


class TestFeedback:
    def test_refuted_steps_are_named_and_unknown_only_soft(self):
        rep = _report([Verdict.VERIFIED, Verdict.REFUTED, Verdict.UNKNOWN], Verdict.REFUTED)
        form = Formalization(problem_prop="(1:ℕ) = 2", steps=[])
        fb = build_feedback(rep, form)
        assert "PROVED that the following steps are FALSE" in fb
        assert "Step 2" in fb and "p1" in fb
        assert "Steps verified correct by Lean 4: 1." in fb
        assert "could not be checked automatically (re-examine them): 3." in fb
        assert "FINAL ANSWER is inconsistent" in fb

    def test_no_false_accusations_when_only_unknown(self):
        rep = _report([Verdict.UNKNOWN], Verdict.UNKNOWN)
        fb = build_feedback(rep, Formalization(problem_prop=None, steps=[]))
        assert "FALSE" not in fb


class TestBenchSummary:
    def test_summary_metrics(self):
        def row(tag, base, fin, flagged, rounds, status, lat):
            return {
                "tags": [tag],
                "baseline_correct": base,
                "final_correct": fin,
                "r1_flagged": flagged,
                "r1_refuted_steps": 1 if flagged else 0,
                "r1_final_verdict": "refuted" if flagged else "verified",
                "rounds": rounds,
                "status": status,
                "latency_s": lat,
            }

        rows = [
            row("math", True, True, False, 1, "verified", 10),
            row("math", False, True, True, 2, "verified", 30),
            row("logic", False, False, False, 3, "max_rounds", 50),
            row("logic", True, True, True, 2, "verified", 20),
        ]
        s = summarize(rows)
        assert s["n"] == 4
        assert s["baseline_accuracy"] == 0.5 and s["verified_accuracy"] == 0.75
        assert s["abs_gain"] == 0.25
        assert s["wrong_baseline"] == 2 and s["wrong_detected_by_lean"] == 1
        assert s["detection_recall"] == 0.5
        assert s["false_alarms_on_correct"] == 1 and s["false_alarm_rate"] == 0.5
        assert s["fixed_after_feedback"] == 1 and s["fix_rate"] == 0.5
        assert s["regressions"] == 0
        assert s["answers_with_refuted_claims_r1"] == 2
        assert s["mean_rounds"] == 2.0

    def test_evaluate_trace_uses_round1_as_baseline(self):
        from falconverifier.schemas import Round, StudentAnswer, Trace

        def rnd(i, final, verdicts, fv):
            return Round(
                round_index=i,
                answer=StudentAnswer(raw="", steps=[], final_answer=final),
                formalization=Formalization(problem_prop=None, steps=[]),
                report=_report(verdicts, fv),
                feedback=None,
            )

        trace = Trace(
            problem="p",
            student_model="s",
            formalizer_model="f",
            rounds=[
                rnd(1, "5", [Verdict.REFUTED], Verdict.REFUTED),
                rnd(2, "6", [Verdict.VERIFIED], Verdict.VERIFIED),
            ],
            final_answer="6",
            status="verified",
            assurance_score=1.0,
        )
        row = evaluate_trace(trace, "6")
        assert row["baseline_answer"] == "5" and row["baseline_correct"] is False
        assert row["final_correct"] is True and row["r1_flagged"] is True


def _formal(*props: str | None, problem: str | None = None) -> Formalization:
    return Formalization(
        problem_prop=problem,
        steps=[
            FormalStep(index=i + 1, kind="arith" if p else "skip", lean_prop=p)
            for i, p in enumerate(props)
        ],
    )


def test_lift_to_rat_handles_bare_literals():
    from falconverifier.verifier import lift_to_rat

    assert lift_to_rat("1 / (1/2) = 2") == "(1:ℚ) / (1/2) = 2"
    assert lift_to_rat("(1:ℚ) / 2 = 0.5") is None
    assert lift_to_rat("17 * 23 = 391") is None
    assert lift_to_rat("(150:ℤ) - 75 = 75") == "(150:ℚ) - 75 = 75"
    assert lift_to_rat("∃ (n : ℕ), n / 2 = 3") is None


def test_answers_match_uses_result_of_equation():
    from falconverifier.bench import answers_match

    assert answers_match("(48 + 41 + 40 + 59 + 67) / 5 = 255 / 5 = 51", "51")
    assert not answers_match("(48 + 41) / 2 = 44", "51")
    assert answers_match("x = 4", "4")


def test_literals_grounded_and_final_grounding():
    from falconverifier.schemas import Formalization, Verdict, VerificationReport
    from falconverifier.verifier import check_final_grounding, literals_grounded

    assert literals_grounded("(24:ℕ) * 46 = 1104", "24 × 46 = 1104", "")
    assert not literals_grounded("(50:ℕ) / 100 * 150 = 75", "50% of 150 is 75", "")

    form = Formalization(problem_prop="(79:ℕ) * 46 - 220 = 3414", steps=[])
    rep = VerificationReport(
        steps=[], final_answer_verdict=Verdict.VERIFIED, lean_file="", lean_latency_s=0
    )
    check_final_grounding("2888", form, rep)
    assert rep.final_answer_verdict == Verdict.REFUTED
    assert rep.final_answer_detail.startswith("inconsistent final answer")

    rep2 = VerificationReport(
        steps=[], final_answer_verdict=Verdict.VERIFIED, lean_file="", lean_latency_s=0
    )
    check_final_grounding("3414 boxes", form, rep2)
    assert rep2.final_answer_verdict == Verdict.VERIFIED


def test_answers_match_arabic_yes_no():
    from falconverifier.bench import answers_match

    assert answers_match("نعم، النتيجة تتبع", "Yes")
    assert not answers_match("نعم", "No")


def test_align_polarity_fixes_dropped_negation():
    from falconverifier.formalizer import align_polarity

    valid = "∀ (A B : Fin 3 → Bool), (∀ x, A x → B x) → (∃ x, A x) → ∃ x, B x"
    # student says "No" but formalizer encoded the positive inference -> negate it
    assert align_polarity(valid, "لا") == f"¬ ({valid})"
    assert align_polarity(valid, "No, it does not follow") == f"¬ ({valid})"
    # student says "Yes" but formalizer negated -> strip the outer negation
    assert align_polarity(f"¬ ({valid})", "نعم") == valid
    # already aligned: untouched
    assert align_polarity(valid, "yes") == valid
    assert align_polarity(f"¬ ({valid})", "no") == f"¬ ({valid})"
    # `¬ (P) ∧ (Q)` is not an outer negation
    mixed = "¬ (∀ x : Fin 3, True) ∧ (∃ x : Fin 3, True)"
    assert align_polarity(mixed, "yes") == mixed
    # arithmetic props and non-yes/no answers are never touched
    assert align_polarity("(3:ℕ) ∣ 12", "no") == "(3:ℕ) ∣ 12"
    assert align_polarity(valid, "391") == valid
    assert align_polarity(None, "no") is None


def test_yes_no_polarity():
    from falconverifier.student import yes_no_polarity

    assert yes_no_polarity("نعم، يلزم") is True
    assert yes_no_polarity("لا، غير صحيح") is False
    assert yes_no_polarity("غير صحيح") is False
    assert yes_no_polarity("No. Yes.") is None
    assert yes_no_polarity("42") is None
    assert yes_no_polarity(None) is None


def test_feedback_mentions_missing_final():
    from falconverifier.schemas import Formalization, Verdict, VerificationReport

    rep = VerificationReport(
        steps=[], final_answer_verdict=Verdict.SKIPPED, lean_file="", lean_latency_s=0.0
    )
    fb = build_feedback(rep, Formalization(steps=[]), missing_final=True)
    assert "FINAL ANSWER" in fb
    fb_ar = build_feedback(rep, Formalization(steps=[]), arabic=True, missing_final=True)
    assert "الجواب النهائي" in fb_ar
