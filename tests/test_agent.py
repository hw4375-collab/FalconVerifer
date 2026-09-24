from __future__ import annotations

import json

from conftest import FakeRunner, ScriptedModel

from falconverifier.agent import VerifyAndTeachAgent, assurance_score
from falconverifier.schemas import Verdict

PROBLEM = "What is 17 * 23?"

WRONG = "Step 1: 17 * 20 = 340.\nStep 2: 17 * 3 = 51.\nStep 3: 340 + 51 = 381.\nFINAL ANSWER: 381"
WRONG_PROSE = (
    "Step 1: Multiplying 17 by 20 gives 340.\nStep 2: Multiplying 17 by 3 gives 51.\n"
    "Step 3: Adding 340 and 51 gives 381.\nFINAL ANSWER: 381"
)
RIGHT = "Step 1: 17 * 20 = 340.\nStep 2: 17 * 3 = 51.\nStep 3: 340 + 51 = 391.\nFINAL ANSWER: 391"


def form_json(step3: str, final: str) -> str:
    return json.dumps(
        {
            "problem_prop": final,
            "steps": [
                {"index": 1, "kind": "arith", "lean_prop": "(17:ℕ) * 20 = 340"},
                {"index": 2, "kind": "arith", "lean_prop": "(17:ℕ) * 3 = 51"},
                {"index": 3, "kind": "arith", "lean_prop": step3},
            ],
        }
    )


TABLE = {
    "(17:ℕ) * 20 = 340": Verdict.VERIFIED,
    "(17:ℕ) * 3 = 51": Verdict.VERIFIED,
    "(340:ℕ) + 51 = 381": Verdict.REFUTED,
    "(340:ℕ) + 51 = 391": Verdict.VERIFIED,
    "(17:ℕ) * 23 = 381": Verdict.REFUTED,
    "(17:ℕ) * 23 = 391": Verdict.VERIFIED,
    "(340:ℕ) + 99 = 381": Verdict.REFUTED,
    "(17:ℕ) * 99 = 381": Verdict.REFUTED,
}


def test_loop_teaches_and_student_fixes(settings):
    student = ScriptedModel([WRONG, RIGHT])
    formalizer = ScriptedModel(
        [
            # grounded arithmetic over the student's own numbers -> no LLM audit is consulted
            form_json("(340:ℕ) + 51 = 381", "(17:ℕ) * 23 = 381"),
            form_json("(340:ℕ) + 51 = 391", "(17:ℕ) * 23 = 391"),
        ]
    )
    events: list[str] = []
    agent = VerifyAndTeachAgent(
        settings,
        student_model=student,
        formalizer_model=formalizer,
        runner=FakeRunner(TABLE),
        on_event=lambda k, p: events.append(k),
    )
    trace = agent.run(PROBLEM, expected_answer="391")

    assert trace.status == "verified"
    assert trace.final_answer == "391"
    assert trace.n_rounds == 2
    assert trace.assurance_score == 1.0
    r1 = trace.rounds[0]
    assert r1.report.steps[2].verdict == Verdict.REFUTED
    assert r1.report.final_answer_verdict == Verdict.REFUTED
    assert r1.feedback and "Step 3" in r1.feedback and "FALSE" in r1.feedback
    # the revision request carried the Lean feedback back to the student
    revision_msgs = student.calls[1]
    assert any("PROVED" in m["content"] for m in revision_msgs if m["role"] == "user")
    assert events.count("round_start") == 2 and "feedback" in events and events[-1] == "done"


def test_unfaithful_refutation_is_downgraded_not_taught(settings):
    # prose steps (outside the pregroup fragment) so the LLM formalizer is used, and props
    # mention numbers the student never wrote (99), so the audit must be consulted
    student = ScriptedModel([WRONG_PROSE])
    formalizer = ScriptedModel(
        [
            form_json("(340:ℕ) + 99 = 381", "(17:ℕ) * 99 = 381"),
            json.dumps({"faithful": False, "reason": "polarity flipped"}),
            json.dumps({"faithful": False, "reason": "polarity flipped"}),
        ]
    )
    agent = VerifyAndTeachAgent(
        settings, student_model=student, formalizer_model=formalizer, runner=FakeRunner(TABLE)
    )
    trace = agent.run(PROBLEM, max_rounds=1)
    rep = trace.rounds[0].report
    assert rep.steps[2].verdict == Verdict.UNKNOWN
    assert rep.final_answer_verdict == Verdict.UNKNOWN
    assert trace.status == "unknown"
    assert len(student.calls) == 1  # never asked to revise


def test_max_rounds_reached_reports_max_rounds(settings):
    student = ScriptedModel([WRONG, WRONG])
    formalizer = ScriptedModel(
        [
            form_json("(340:ℕ) + 51 = 381", "(17:ℕ) * 23 = 381"),
            form_json("(340:ℕ) + 51 = 381", "(17:ℕ) * 23 = 381"),
        ]
    )
    agent = VerifyAndTeachAgent(
        settings,
        student_model=student,
        formalizer_model=formalizer,
        runner=FakeRunner(TABLE),
        audit_refutations=False,
    )
    trace = agent.run(PROBLEM, max_rounds=2)
    assert trace.status == "max_rounds"
    assert trace.assurance_score < 0.5
    assert trace.rounds[-1].feedback is None


def test_ill_formed_triggers_one_repair(settings):
    bad = json.dumps(
        {
            "problem_prop": "(17:ℕ) * 23 = 391",
            "steps": [{"index": 1, "kind": "arith", "lean_prop": "undefined_symbol = 1"}],
        }
    )
    good = json.dumps(
        {
            "problem_prop": "(17:ℕ) * 23 = 391",
            "steps": [{"index": 1, "kind": "arith", "lean_prop": "(17:ℕ) * 20 = 340"}],
        }
    )
    student = ScriptedModel(["Step 1: Multiplying 17 by 20 gives 340\nFINAL ANSWER: 391"])
    formalizer = ScriptedModel([bad, good])
    runner = FakeRunner({**TABLE, "undefined_symbol = 1": Verdict.ILL_FORMED})
    agent = VerifyAndTeachAgent(
        settings, student_model=student, formalizer_model=formalizer, runner=runner
    )
    trace = agent.run(PROBLEM)
    assert len(runner.seen) == 2
    assert trace.rounds[0].report.steps[0].verdict == Verdict.VERIFIED
    assert trace.status == "verified"
    repair_request = [m for m in formalizer.calls[1] if m["role"] == "user"][-1]["content"]
    assert "step 1" in repair_request.lower()


def test_assurance_score_shape():
    assert assurance_score(None) == 0.0


def test_degenerate_yes_no_prop_gives_no_assurance(settings):
    problem = "If 6 divides n then 3 divides n. 3 divides 18. Does it follow that 6 divides 18?"
    student = ScriptedModel(["Step 1: 3 divides 18 is given.\nFINAL ANSWER: Yes"])
    degenerate = "∀ (n : ℕ), 6 ∣ n → 3 ∣ n → 6 ∣ n"
    formalizer = ScriptedModel(
        [json.dumps({"problem_prop": degenerate, "steps": [{"index": 1, "kind": "skip"}]})]
    )
    agent = VerifyAndTeachAgent(
        settings,
        student_model=student,
        formalizer_model=formalizer,
        runner=FakeRunner({degenerate: Verdict.VERIFIED}),
    )
    trace = agent.run(problem, expected_answer="No", max_rounds=1)
    assert trace.status == "unknown"
    assert trace.rounds[0].report.final_answer_verdict == Verdict.UNKNOWN
    assert "degenerate" in trace.rounds[0].report.final_answer_detail
