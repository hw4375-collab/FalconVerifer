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


def test_counterexample_search_refutes_false_universals(runner: LeanRunner):
    res = runner.check_claims(
        {
            "div3_div6": "∀ (n : ℕ), n % 3 = 0 → n % 6 = 0",
            "not_div3_div6": "¬ (∀ (n : ℕ), n % 3 = 0 → n % 6 = 0)",
            "div6_div3": "∀ (n : ℕ), n % 6 = 0 → n % 3 = 0",
            "not_transitive": "¬ (∀ (a b c : ℤ), a > b → b > c → a > c)",
            "sq_nonneg": "∀ (x : ℝ), x ^ 2 - 2 * x + 1 ≥ 0",
        }
    )
    v = {k: o.verdict for k, o in res.outcomes.items()}
    assert v["div3_div6"] == Verdict.REFUTED
    assert v["not_div3_div6"] == Verdict.VERIFIED
    assert v["div6_div3"] == Verdict.VERIFIED
    assert v["not_transitive"] == Verdict.REFUTED
    assert v["sq_nonneg"] == Verdict.VERIFIED


@requires_lean
def test_arabic_logic_fragment_is_decided_both_ways(runner):
    """Every syllogism/propositional/order item of the Arabic set that the fragment covers is
    settled by the kernel in the direction of its answer key, and its negation the other way."""
    import json

    from falconverifier.arabic_logic import formalize_logic_problem

    claims, expected = {}, {}
    for line in (LEAN_DIR.parent / "bench" / "problems_ar.jsonl").read_text().splitlines():
        d = json.loads(line)
        hit = formalize_logic_problem(d["problem"]) if d["id"].startswith("arlogic") else None
        if hit:
            k = d["id"].replace("-", "_")
            claims[k + "_pos"], claims[k + "_neg"] = hit[0], f"¬ ({hit[0]})"
            expected[k] = d["answer"] == "نعم"
    assert len(expected) >= 16
    res = runner.check_claims(claims)
    for k, yes in expected.items():
        pos, neg = res.outcomes[k + "_pos"].verdict, res.outcomes[k + "_neg"].verdict
        assert (pos, neg) == (
            (Verdict.VERIFIED, Verdict.REFUTED) if yes else (Verdict.REFUTED, Verdict.VERIFIED)
        ), k


def test_regular_graph_claims_use_lemmas_not_enumeration(runner: LeanRunner):
    """`FalconVerifier.Regular` claims must be settled by the handshake lemma / circulant
    witness in seconds; a generic `decide` over `Fin 5 → Fin 5 → Bool` (2^25 relations) dies
    with an unrecoverable max-recursion error, which is exactly what this guards against."""
    res = runner.check_claims(
        {
            "five_three_lie": "∀ f : Fin 5 → Fin 5 → Bool, ¬ FalconVerifier.Regular f 3",
            "five_three_no": "¬ (∀ f : Fin 5 → Fin 5 → Bool, ¬ FalconVerifier.Regular f 3)",
            "six_three_possible": "∃ f : Fin 6 → Fin 6 → Bool, FalconVerifier.Regular f 3",
            "seven_three_possible": "∃ f : Fin 7 → Fin 7 → Bool, FalconVerifier.Regular f 3",
            "four_four_lie": "∀ f : Fin 4 → Fin 4 → Bool, ¬ FalconVerifier.Regular f 4",
            "eight_five_possible": "∃ f : Fin 8 → Fin 8 → Bool, FalconVerifier.Regular f 5",
        }
    )
    v = {k: o.verdict for k, o in res.outcomes.items()}
    assert v["five_three_lie"] == Verdict.VERIFIED
    assert v["five_three_no"] == Verdict.REFUTED
    assert v["six_three_possible"] == Verdict.VERIFIED
    assert v["seven_three_possible"] == Verdict.REFUTED
    assert v["four_four_lie"] == Verdict.VERIFIED
    assert v["eight_five_possible"] == Verdict.VERIFIED
    assert res.latency_s < 60


def test_arabic_word_problems_decided_by_kernel(runner: LeanRunner):
    """Quantity narratives (multiply-then-subtract, compound discount, whole boxes, average)
    from the deterministic word fragment: gold answers verified, off-by-one answers refuted."""
    from falconverifier.arabic_word import formalize_word_problem as f

    boxes = (
        "اشترى سعيد ٩٣ علبة تحتوي كل منها على ٣٧ صندوقاً، ثم أعطى ٣٩١ صندوقاً من مجموعها "
        "لأصدقائه. كم صندوقاً بقي لدى سعيد؟"
    )
    disc = (
        "يبلغ سعر هاتف 800 درهماً. خُفِّض بنسبة 10٪ ثم خُفِّض السعر الجديد بنسبة 20٪ أخرى. "
        "ما هو السعر النهائي بالدرهم؟"
    )
    full = "لدينا ٨٧ تفاحة نضعها في صناديق تتسع كل منها ٦ تفاحة. كم صندوقاً ممتلئاً نحصل عليه؟"
    avg = "حصلت ليلى على الدرجات ٨٥، ٩٠، ٧٨ في ٣ اختبارات. ما هو متوسط درجاتها؟"
    cases = {
        "boxes_ok": (boxes, "3050", Verdict.VERIFIED),
        "boxes_bad": (boxes, "172", Verdict.REFUTED),
        "disc_ok": (disc, "576", Verdict.VERIFIED),
        "disc_bad": (disc, "560", Verdict.REFUTED),
        "full_ok": (full, "14", Verdict.VERIFIED),
        "full_bad": (full, "15", Verdict.REFUTED),
        "avg_ok": (avg, "84.33", Verdict.VERIFIED),
        "avg_bad": (avg, "85", Verdict.REFUTED),
    }
    claims = {k: f(p, a)[0] for k, (p, a, _) in cases.items()}  # type: ignore[index]
    res = runner.check_claims(claims)
    for k, (_, _, want) in cases.items():
        assert res.outcomes[k].verdict == want, (k, claims[k], res.outcomes[k].detail)
