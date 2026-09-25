from __future__ import annotations

import json

from conftest import ScriptedModel

from falconverifier.agent import VerifyAndTeachAgent
from falconverifier.formalizer import Formalizer
from falconverifier.lean_runner import LeanRunner
from falconverifier.memory import Memory, env_fingerprint, normalize
from falconverifier.schemas import LeanDiagnostic, ReasoningStep, Verdict


def test_normalize_unifies_digits_whitespace_diacritics():
    assert normalize("كَمْ  ٥ + ٣؟") == normalize("كم 5 + 3؟")
    assert Memory.problem_key("ما هو ٧ × ٨؟") == Memory.problem_key("ما هو 7 ×   8؟")


def test_lean_memory_stores_only_decisive_verdicts(tmp_path):
    mem = Memory(tmp_path / "m.sqlite")
    mem.put_verdict("env1", "(2:ℕ) + 2 = 4", "fv_auto", Verdict.VERIFIED, "")
    mem.put_verdict("env1", "(2:ℕ) + 2 = 5", "fv_auto", Verdict.UNKNOWN, "timeout")
    assert mem.get_verdict("env1", "(2:ℕ)  +  2 = 4", "fv_auto").verdict == Verdict.VERIFIED
    assert mem.get_verdict("env1", "(2:ℕ) + 2 = 5", "fv_auto") is None
    # a different toolchain/prelude fingerprint never reuses a verdict
    assert mem.get_verdict("env2", "(2:ℕ) + 2 = 4", "fv_auto") is None
    s = mem.summary()
    assert s["lean_claims"]["stored"] == 1 and s["lean_claims"]["hits"] == 1


def test_env_fingerprint_tracks_prelude_changes(tmp_path):
    (tmp_path / "lean-toolchain").write_text("leanprover/lean4:v4.0.0")
    src = tmp_path / "FalconVerifier"
    src.mkdir()
    (src / "Prelude.lean").write_text("theorem a : True := trivial")
    f1 = env_fingerprint(tmp_path, "header")
    (src / "Prelude.lean").write_text("theorem a : True := by trivial")
    f2 = env_fingerprint(tmp_path, "header")
    assert f1 != f2
    assert env_fingerprint(tmp_path, "other header") != f2


class _CountingRunner(LeanRunner):
    """LeanRunner whose compiler is a table lookup, so we can count real compilations."""

    def __init__(self, project_dir, memory):
        super().__init__(project_dir, memory=memory)
        self.compiles = 0

    def _compile(self, source: str) -> list[LeanDiagnostic]:
        self.compiles += 1
        diags = []
        for i, line in enumerate(source.split("\n"), start=1):
            # every claim `= 4` is true (¬ fails), every `= 5` is false (P fails)
            if line.startswith("theorem") and line.endswith("fv_auto"):
                is_neg = "_neg :" in line
                true_claim = "= 4" in line
                if is_neg == true_claim:
                    diags.append(LeanDiagnostic(line=i, severity="error", message="unsolved"))
        return diags


def test_runner_serves_repeated_claims_from_memory(tmp_path):
    mem = Memory(tmp_path / "m.sqlite")
    runner = _CountingRunner(tmp_path, mem)
    r1 = runner.check_claims({"a": "(2:ℕ) + 2 = 4", "b": "(2:ℕ) + 2 = 5"})
    assert r1.outcomes["a"].verdict == Verdict.VERIFIED
    assert r1.outcomes["b"].verdict == Verdict.REFUTED
    assert r1.cache_hits == 0 and runner.compiles == 1

    r2 = runner.check_claims({"x": "(2:ℕ) + 2 = 4", "y": "(2:ℕ) + 2 = 5"})
    assert runner.compiles == 1  # nothing recompiled
    assert r2.cache_hits == 2
    assert r2.outcomes["x"].verdict == Verdict.VERIFIED and r2.outcomes["x"].cached
    assert "memory" in r2.outcomes["x"].detail
    assert "served from kernel memory" in r2.source

    r3 = runner.check_claims({"x": "(2:ℕ) + 2 = 4", "z": "(1:ℕ) + 3 = 4"})
    assert runner.compiles == 2 and r3.cache_hits == 1
    assert r3.outcomes["z"].verdict == Verdict.VERIFIED and not r3.outcomes["z"].cached


def _report_for(form, verdict=Verdict.VERIFIED):
    from falconverifier.schemas import StepResult, VerificationReport

    return VerificationReport(
        steps=[
            StepResult(
                index=fs.index, verdict=verdict, lean_prop=fs.lean_prop, step_text=f"t{fs.index}"
            )
            for fs in form.steps
        ],
        final_answer_verdict=verdict,
        lean_file="",
        lean_latency_s=0.0,
    )


def test_formalizer_reuses_remembered_translations(tmp_path):
    mem = Memory(tmp_path / "m.sqlite")
    reply = json.dumps(
        {
            "problem_prop": "(45:ℕ) * 24 - 380 = 700",
            "steps": [
                {"index": 1, "kind": "arith", "lean_prop": "(45:ℕ) * 24 = 1080"},
                {"index": 2, "kind": "skip"},
            ],
        }
    )
    model = ScriptedModel([reply, "{}"], model="fmz")
    fz = Formalizer(model, memory=mem)
    problem = "Khalid bought 45 boxes of 24 pens and gave away 380. How many remain?"
    steps = [
        ReasoningStep(index=1, text="Multiplying 45 by 24 gives 1080 pens"),
        ReasoningStep(index=2, text="Now we subtract what he gave away"),
    ]
    form, _ = fz.formalize(problem, steps, "700")
    assert len(model.calls) == 1 and fz.last_memory_hits == 0
    fz.remember(problem, steps, "700", form, _report_for(form))

    form2, _ = fz.formalize(problem, steps, "700")
    assert len(model.calls) == 1  # no second LLM call
    assert fz.last_memory_hits == 3  # two steps + problem claim
    assert form2.raw == "memory"
    assert form2.steps[0].lean_prop == "(45:ℕ) * 24 = 1080"
    assert form2.steps[0].note.startswith("memory:")
    assert form2.steps[1].lean_prop is None
    assert form2.problem_prop == "(45:ℕ) * 24 - 380 = 700"

    # a partially new answer only sends the unseen sentence to the model
    steps3 = steps + [ReasoningStep(index=3, text="1080 minus 380 is 700")]
    fz.formalize(problem, steps3, "700")
    assert len(model.calls) == 2
    user_msg = [m for m in model.calls[1] if m["role"] == "user"][-1]["content"]
    assert "Step 3" in user_msg and "Step 1" not in user_msg


def test_ill_formed_translations_are_not_remembered(tmp_path):
    mem = Memory(tmp_path / "m.sqlite")
    reply = json.dumps(
        {"problem_prop": None, "steps": [{"index": 1, "kind": "arith", "lean_prop": "bogus x"}]}
    )
    model = ScriptedModel([reply, reply], model="fmz")
    fz = Formalizer(model, memory=mem)
    steps = [ReasoningStep(index=1, text="something odd happens here")]
    form, _ = fz.formalize("P?", steps, None)
    fz.remember("P?", steps, None, form, _report_for(form, Verdict.ILL_FORMED))
    fz.formalize("P?", steps, None)
    assert len(model.calls) == 2


def test_agent_records_memory_and_recognises_repeated_problem(settings):
    from conftest import FakeRunner

    mem = Memory(settings.runs_dir / "m.sqlite")
    table = {"(17:ℕ) * 23 = 391": Verdict.VERIFIED, "(17:ℕ) * 20 = 340": Verdict.VERIFIED}
    answer = "Step 1: 17 * 20 = 340.\nFINAL ANSWER: 391"
    form = json.dumps(
        {
            "problem_prop": "(17:ℕ) * 23 = 391",
            "steps": [{"index": 1, "kind": "arith", "lean_prop": "(17:ℕ) * 20 = 340"}],
        }
    )

    def make():
        return VerifyAndTeachAgent(
            settings,
            student_model=ScriptedModel([answer]),
            formalizer_model=ScriptedModel([form]),
            runner=FakeRunner(table),
            memory=mem,
        )

    a1 = make()
    t1 = a1.run("What is 17 * 23?", expected_answer="391")
    assert "seen_before" not in t1.memory
    a1.save_trace(t1)

    t2 = make().run("What is 17  *  23?")  # same problem, different whitespace, no expected
    assert t2.memory["seen_before"] == 1
    assert t2.memory["last_status"] == "verified"
    assert t2.expected_answer == "391" and t2.memory["expected_answer_from_memory"]
    assert len(t2.memory["prior_traces"]) == 1
