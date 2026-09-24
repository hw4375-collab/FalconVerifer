from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from falconverifier.lean_runner import ClaimOutcome, LeanRunResult
from falconverifier.llm import ChatResponse
from falconverifier.schemas import Verdict

REPO = Path(__file__).resolve().parent.parent
LEAN_DIR = REPO / "lean"


def lean_available() -> bool:
    return shutil.which("lake") is not None and (LEAN_DIR / ".lake").exists()


requires_lean = pytest.mark.skipif(not lean_available(), reason="Lean/Mathlib not built")


class ScriptedModel:
    """ChatModel that replays canned replies in order (or by substring match)."""

    def __init__(self, replies: list[str], model: str = "scripted"):
        self.replies = list(replies)
        self.model = model
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, *, temperature=0.0, max_tokens=2048) -> ChatResponse:
        self.calls.append(messages)
        content = self.replies.pop(0) if self.replies else "{}"
        return ChatResponse(
            content=content,
            reasoning=None,
            model=self.model,
            prompt_tokens=0,
            completion_tokens=0,
            latency_s=0.0,
        )


class FakeRunner:
    """Lean stand-in: verdict decided by a lookup table on the prop text."""

    def __init__(self, table: dict[str, Verdict]):
        self.table = table
        self.seen: list[dict[str, str]] = []

    def check_claims(self, claims: dict[str, str]) -> LeanRunResult:
        self.seen.append(dict(claims))
        outcomes = {
            cid: ClaimOutcome(self.table.get(p, Verdict.UNKNOWN), "") for cid, p in claims.items()
        }
        return LeanRunResult(outcomes, [], "", 0.0)


@pytest.fixture
def settings(tmp_path):
    from falconverifier.config import LLMEndpoint, Settings

    ep = LLMEndpoint(base_url="http://x", api_key="k", model="m")
    return Settings(student=ep, formalizer=ep, lean_project_dir=tmp_path, runs_dir=tmp_path)
