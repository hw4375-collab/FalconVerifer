from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

# FORMALIZER_PROVIDER selects who translates NL -> Lean. "falcon" (default) keeps the
# whole loop inside the Falcon family; the others are optional stronger formalizers
# used as a comparison arm in the benchmark.
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "falcon": {
        "base_url": "https://chat.falconllm.tii.ae/api",
        "key_env": "FALCON_API_KEY",
        "model": "falcon-h1-arabic-34b-instruct",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
        "model": "gpt-4.1-mini",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "model": "google/gemma-4-31b-it:free",
    },
}


@dataclass
class LLMEndpoint:
    base_url: str
    api_key: str
    model: str
    timeout: float = 300.0


@dataclass
class Settings:
    student: LLMEndpoint
    formalizer: LLMEndpoint
    lean_project_dir: Path
    max_rounds: int = 3
    lean_timeout: float = 120.0
    runs_dir: Path = field(default_factory=lambda: REPO_ROOT / "runs")

    @classmethod
    def from_env(cls, provider: str | None = None) -> Settings:
        falcon_url = os.getenv("FALCON_BASE_URL", "https://chat.falconllm.tii.ae/api").rstrip("/")
        falcon_key = os.getenv("FALCON_API_KEY", "")
        student = LLMEndpoint(
            base_url=falcon_url,
            api_key=falcon_key,
            model=os.getenv("FALCON_STUDENT_MODEL", "falcon-h1-7b-instruct"),
        )
        provider = (provider or os.getenv("FORMALIZER_PROVIDER", "falcon")).lower()
        preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["falcon"])
        default_url = falcon_url if provider == "falcon" else preset["base_url"]
        default_key = falcon_key if provider == "falcon" else os.getenv(preset["key_env"], "")
        default_model = (
            os.getenv("FALCON_FORMALIZER_MODEL", preset["model"])
            if provider == "falcon"
            else preset["model"]
        )
        formalizer = LLMEndpoint(
            base_url=os.getenv("FORMALIZER_BASE_URL", default_url).rstrip("/"),
            api_key=os.getenv("FORMALIZER_API_KEY", default_key),
            model=os.getenv("FORMALIZER_MODEL", default_model),
        )
        lean_dir = Path(os.getenv("LEAN_PROJECT_DIR", REPO_ROOT / "lean"))
        if not lean_dir.is_absolute():
            lean_dir = (REPO_ROOT / lean_dir).resolve()
        return cls(
            student=student,
            formalizer=formalizer,
            lean_project_dir=lean_dir,
            max_rounds=int(os.getenv("MAX_ROUNDS", "3")),
            lean_timeout=float(os.getenv("LEAN_TIMEOUT", "120")),
        )
