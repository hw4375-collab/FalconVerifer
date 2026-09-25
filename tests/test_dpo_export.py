import json
from pathlib import Path

from falconverifier.dpo_export import export, pairs_from_trace

PROBLEM = "سعر هاتف 800 درهم، خُفِّض 10٪ ثم 20٪. ما السعر النهائي؟"
FINAL_PROP = "(800:ℝ) * (1 - 0.10) * (1 - 0.20) = 576"


def _round(idx, raw, final, final_verdict, steps, feedback=None, prop=FINAL_PROP):
    return {
        "round_index": idx,
        "answer": {"raw": raw, "final_answer": final, "steps": []},
        "formalization": {"problem_prop": prop, "steps": []},
        "report": {
            "steps": [
                {"index": i, "verdict": v, "lean_prop": p, "step_text": t, "detail": ""}
                for i, (v, p, t) in enumerate(steps, 1)
            ],
            "final_answer_verdict": final_verdict,
            "final_answer_detail": "kernel proved the negation"
            if final_verdict == "refuted"
            else "",
        },
        "feedback": feedback,
    }


GOOD_STEPS = [
    ("verified", "(800:ℝ) - 80 = 720", "800 - 80 = 720"),
    ("verified", "(720:ℝ) - 144 = 576", "720 - 144 = 576"),
]


def _trace(rounds, expected="576"):
    t = {
        "problem": PROBLEM,
        "student_model": "falcon-h1-arabic-3b-instruct",
        "formalizer_model": "falcon-h1-arabic-34b-instruct",
        "rounds": rounds,
    }
    if expected is not None:
        t["expected_answer"] = expected
    return t


def test_refuted_then_verified_yields_one_pair_with_lean_evidence():
    trace = _trace(
        [
            _round(0, "... الجواب النهائي: 680", "680", "refuted", GOOD_STEPS, "fb-ar"),
            _round(1, "... الجواب النهائي: 576", "576", "verified", GOOD_STEPS),
        ]
    )
    pairs = pairs_from_trace(trace, "t.json")
    assert len(pairs) == 1
    p = pairs[0]
    assert p.prompt == PROBLEM
    assert p.rejected.endswith("680") and p.chosen.endswith("576")
    assert p.evidence.feedback == "fb-ar"
    assert p.evidence.refuted_claims == [
        {
            "step": "final",
            "text": "",
            "lean_prop": FINAL_PROP,
            "detail": "kernel proved the negation",
        }
    ]
    assert p.evidence.chosen_claims == ["(800:ℝ) - 80 = 720", "(720:ℝ) - 144 = 576"]
    assert p.meta["lang"] == "ar"
    assert (p.meta["rejected_round"], p.meta["chosen_round"]) == (0, 1)


def test_refuted_step_is_recorded_as_evidence():
    steps_bad = [("refuted", "(36:ℚ) + 9 * 8 - 3 ^ 2 = 66", "36 + 72 - 9 = 66")]
    trace = _trace(
        [
            _round(0, "A 66", "66", "unknown", steps_bad, "fb"),
            _round(1, "A 99", "99", "verified", [("verified", "(36:ℚ)+9*8-3^2 = 99", "")]),
        ],
        expected="99",
    )
    (p,) = pairs_from_trace(trace)
    assert p.evidence.refuted_claims[0]["step"] == "1"
    assert p.evidence.refuted_claims[0]["lean_prop"].endswith("= 66")


def test_no_pair_when_chosen_disagrees_with_gold_answer():
    """A Lean 'verified' on an unfaithful formalization must never become 'chosen'."""
    trace = _trace(
        [
            _round(0, "A 576", "576", "refuted", GOOD_STEPS, "false alarm"),
            _round(1, "A 680", "680", "verified", GOOD_STEPS),
        ],
        expected="576",
    )
    assert pairs_from_trace(trace) == []


def test_no_pair_without_lean_refutation_or_without_verified_end():
    both_ok = _trace([_round(0, "A 576", "576", "verified", GOOD_STEPS)])
    assert pairs_from_trace(both_ok) == []
    never_fixed = _trace(
        [
            _round(0, "A 680", "680", "refuted", GOOD_STEPS, "fb"),
            _round(1, "A 680", "680", "refuted", GOOD_STEPS, "fb"),
        ]
    )
    assert pairs_from_trace(never_fixed) == []
    unknown_end = _trace(
        [
            _round(0, "A 680", "680", "refuted", GOOD_STEPS, "fb"),
            _round(1, "A 576", "576", "unknown", GOOD_STEPS),
        ]
    )
    assert pairs_from_trace(unknown_end) == []


def test_chosen_round_must_have_no_refuted_steps():
    trace = _trace(
        [
            _round(0, "A 680", "680", "refuted", GOOD_STEPS, "fb"),
            _round(1, "A 576", "576", "verified", [("refuted", "(1:ℚ) = 2", "1 = 2")]),
        ]
    )
    assert pairs_from_trace(trace) == []


def test_unlabeled_traces_are_skipped_unless_allowed():
    rounds = [
        _round(0, "A 680", "680", "refuted", GOOD_STEPS, "fb"),
        _round(1, "A 576", "576", "verified", GOOD_STEPS),
    ]
    trace = _trace(rounds, expected=None)
    assert pairs_from_trace(trace) == []
    assert len(pairs_from_trace(trace, require_expected=False)) == 1


def test_export_dedupes_and_skips_non_traces(tmp_path: Path):
    rounds = [
        _round(0, "A 680", "680", "refuted", GOOD_STEPS, "fb"),
        _round(1, "A 576", "576", "verified", GOOD_STEPS),
    ]
    d = tmp_path / "run"
    d.mkdir()
    (d / "a.json").write_text(json.dumps(_trace(rounds)), encoding="utf-8")
    (d / "b.json").write_text(json.dumps(_trace(rounds)), encoding="utf-8")
    (d / "results.json").write_text(json.dumps({"summary": {}}), encoding="utf-8")
    (d / "junk.json").write_text("not json", encoding="utf-8")
    out = tmp_path / "pairs.jsonl"
    stats = export([d], out)
    assert stats == {"traces": 2, "pairs": 1, "duplicates": 1, "ar": 1, "en": 0}
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert set(rows[0]) == {"id", "prompt", "chosen", "rejected", "evidence", "meta"}
