from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    VERIFIED = "verified"  # Lean proved the step's claim
    REFUTED = "refuted"  # Lean proved the negation of the claim -> definite error
    UNKNOWN = "unknown"  # well-formed, but automation could neither prove nor refute
    ILL_FORMED = "ill_formed"  # the Lean statement itself does not type-check
    SKIPPED = "skipped"  # step carries no checkable mathematical content


class ReasoningStep(BaseModel):
    index: int
    text: str


class StudentAnswer(BaseModel):
    """One answer from the model under test (Falcon)."""

    raw: str
    reasoning: str | None = None  # hidden chain-of-thought if the model exposes it
    steps: list[ReasoningStep]
    final_answer: str | None
    latency_s: float = 0.0
    tokens: int = 0


class FormalStep(BaseModel):
    """Lean 4 rendering of one reasoning step."""

    index: int
    kind: str = Field(description="arith | algebra | logic | skip")
    lean_prop: str | None = Field(description="A Lean 4 `Prop` (no `theorem`, no proof)")
    note: str = ""


class Formalization(BaseModel):
    problem_prop: str | None = Field(
        default=None,
        description="Lean Prop asserting the problem's final answer claim (if formalizable)",
    )
    problem_note: str = Field(
        default="", description="`pregroup: …` derivation certificate when the grammar produced it"
    )
    steps: list[FormalStep]
    raw: str = ""
    latency_s: float = 0.0


class LeanDiagnostic(BaseModel):
    line: int
    severity: str
    message: str


class StepResult(BaseModel):
    index: int
    verdict: Verdict
    lean_prop: str | None
    step_text: str
    detail: str = ""  # Lean message that justified the verdict (for refuted/ill_formed)


class VerificationReport(BaseModel):
    steps: list[StepResult]
    final_answer_verdict: Verdict
    final_answer_detail: str = ""
    lean_file: str
    lean_latency_s: float
    diagnostics: list[LeanDiagnostic] = []

    @property
    def refuted(self) -> list[StepResult]:
        return [s for s in self.steps if s.verdict == Verdict.REFUTED]

    @property
    def verified(self) -> list[StepResult]:
        return [s for s in self.steps if s.verdict == Verdict.VERIFIED]

    @property
    def unknown(self) -> list[StepResult]:
        return [s for s in self.steps if s.verdict == Verdict.UNKNOWN]

    @property
    def has_errors(self) -> bool:
        return bool(self.refuted) or self.final_answer_verdict == Verdict.REFUTED

    def summary(self) -> dict[str, int]:
        counts = {v.value: 0 for v in Verdict}
        for s in self.steps:
            counts[s.verdict.value] += 1
        return counts


class Round(BaseModel):
    round_index: int
    answer: StudentAnswer
    formalization: Formalization | None
    report: VerificationReport | None
    feedback: str | None  # the teaching message sent back to the student (None on last round)


class Trace(BaseModel):
    """Full assurance trace of one problem solved through the verify-and-teach loop."""

    problem: str
    expected_answer: str | None = None
    student_model: str
    formalizer_model: str
    rounds: list[Round]
    final_answer: str | None
    status: str  # verified | refuted | unknown | max_rounds
    assurance_score: float = Field(ge=0, le=1)
    total_latency_s: float = 0.0

    @property
    def n_rounds(self) -> int:
        return len(self.rounds)
