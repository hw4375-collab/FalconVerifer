"""Talks to the real Lean 4 kernel; skipped when the Lake project is not built."""

from __future__ import annotations

import pytest
from conftest import LEAN_DIR, requires_lean

from falconverifier.lean_runner import LeanRunner
from falconverifier.schemas import Verdict

pytestmark = requires_lean


@pytest.fixture(scope="module")
def runner() -> LeanRunner:
    return LeanRunner(LEAN_DIR, timeout=300)


def test_arith_logic_and_illformed_in_one_batch(runner: LeanRunner):
    res = runner.check_claims(
        {
            "mul_ok": "(17:ℕ) * 23 = 391",
            "mul_bad": "(17:ℕ) * 23 = 381",
            "rat_ok": "(15:ℚ) * ((2:ℚ) / 3) = 10",
            "pct_bad": "(120:ℚ) * (1 - 25/100) * (1 + 10/100) = 100",
            "syllogism_valid": "∀ (A B C : Fin 3 → Bool), (∀ x, A x → B x) → (∀ x, B x → C x) → ∀ x, A x → C x",
            "affirm_consequent": "∀ (P Q : Prop), (P → Q) → Q → P",
            "not_affirm_consequent": "¬ (∀ (P Q : Prop), (P → Q) → Q → P)",
            "undefined": "foo_bar_baz = 3",
            "divisible": "(3:ℕ) ∣ 7 * 12 + 5",
        }
    )
    v = {k: o.verdict for k, o in res.outcomes.items()}
    assert v["mul_ok"] == Verdict.VERIFIED
    assert v["mul_bad"] == Verdict.REFUTED
    assert v["rat_ok"] == Verdict.VERIFIED
    assert v["pct_bad"] == Verdict.REFUTED
    assert v["syllogism_valid"] == Verdict.VERIFIED
    assert v["affirm_consequent"] == Verdict.REFUTED
    assert v["not_affirm_consequent"] == Verdict.VERIFIED
    assert v["undefined"] == Verdict.ILL_FORMED
    assert v["divisible"] == Verdict.REFUTED
    assert res.latency_s < 200


def test_empty_batch_is_free(runner: LeanRunner):
    res = runner.check_claims({})
    assert res.outcomes == {} and res.latency_s == 0.0


def test_rat_lift_retracts_truncation_refutation(runner: LeanRunner):
    from falconverifier.schemas import (
        Formalization,
        FormalStep,
        StepResult,
        VerificationReport,
    )
    from falconverifier.verifier import lift_to_rat, recheck_refutations_over_rat

    assert lift_to_rat("(17:ℕ) * 20 = 340") is None
    assert lift_to_rat("(50:ℕ) / 100 * (150:ℕ) = 75") == "(50:ℚ) / 100 * (150:ℚ) = 75"

    form = Formalization(
        problem_prop="(150:ℕ) + (150:ℕ) * 50 / 100 = 225",
        steps=[
            FormalStep(index=1, kind="arith", lean_prop="(50:ℕ) / 100 * (150:ℕ) = 75", note=""),
            FormalStep(index=2, kind="arith", lean_prop="(7:ℕ) / 2 = 4", note=""),
        ],
    )
    report = VerificationReport(
        steps=[
            StepResult(
                index=1,
                verdict=Verdict.REFUTED,
                lean_prop=form.steps[0].lean_prop,
                step_text="50% of 150 is 75",
                detail="",
            ),
            StepResult(
                index=2,
                verdict=Verdict.REFUTED,
                lean_prop=form.steps[1].lean_prop,
                step_text="7 / 2 = 4",
                detail="",
            ),
        ],
        final_answer_verdict=Verdict.VERIFIED,
        final_answer_detail="",
        lean_file="",
        lean_latency_s=0.0,
    )
    recheck_refutations_over_rat(runner, form, report)
    assert report.steps[0].verdict == Verdict.VERIFIED
    assert report.steps[0].lean_prop == "(50:ℚ) / 100 * (150:ℚ) = 75"
    assert report.steps[1].verdict == Verdict.REFUTED  # 7/2 = 4 is false over ℚ too


def test_pregroup_props_are_decidable_by_fv_auto(runner: LeanRunner):
    """Every Lean Prop the Arabic grammar emits must be closed by the tactic bundle."""
    from falconverifier import arabic

    cases = {
        "mul_ok": ("١٧ × ٢٣ = ٣٩١", Verdict.VERIFIED),
        "sum_bad": ("مجموع ٣٤٠ و ٥١ هو ٣٨١", Verdict.REFUTED),
        "pct_ok": ("٥٠٪ من ١٥٠ يساوي ٧٥", Verdict.VERIFIED),
        "half_ok": ("نصف 45 هو 22.5", Verdict.VERIFIED),
        "sq_ok": ("مربع 7 هو 49", Verdict.VERIFIED),
        "dvd_ok": ("12 يقبل القسمة على 3", Verdict.VERIFIED),
        "ndvd_ok": ("١٣ لا يقبل القسمة على ٣", Verdict.VERIFIED),
        "gt_bad": ("٥ أكبر من ٧", Verdict.REFUTED),
        "nested_ok": ("ضعف مجموع 3 و 4 هو 14", Verdict.VERIFIED),
        "discount_ok": ("٢٠٠ ناقص ٢٠٪ من ٢٠٠ يساوي ١٦٠", Verdict.VERIFIED),
    }
    claims = {k: arabic.formalize_step(t)[0] for k, (t, _) in cases.items()}
    res = runner.check_claims(claims)
    for k, (_, want) in cases.items():
        assert res.outcomes[k].verdict == want, (k, claims[k], res.outcomes[k])
