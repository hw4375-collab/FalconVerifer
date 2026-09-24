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
