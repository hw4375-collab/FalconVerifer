from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol

import httpx

from .config import LLMEndpoint

log = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    content: str
    reasoning: str | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float


class ChatModel(Protocol):
    model: str

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> ChatResponse: ...


class OpenAICompatibleClient:
    """Minimal client for any OpenAI-compatible `/chat/completions` endpoint.

    Works against the Falcon Open WebUI gateway (chat.falconllm.tii.ae/api), vLLM,
    OpenAI, etc. Captures the optional `reasoning` field (chain-of-thought) returned by
    reasoning models such as `falcon-h1r-7b`.
    """

    def __init__(self, endpoint: LLMEndpoint, retries: int = 3):
        self.endpoint = endpoint
        self.model = endpoint.model
        self.retries = retries
        self._client = httpx.Client(
            base_url=endpoint.base_url,
            headers={"Authorization": f"Bearer {endpoint.api_key}"},
            timeout=endpoint.timeout,
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> ChatResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        last_err: Exception | None = None
        for attempt in range(self.retries):
            t0 = time.time()
            try:
                r = self._client.post("/chat/completions", json=payload)
                r.raise_for_status()
                data = r.json()
                choice = data["choices"][0]
                msg = choice["message"]
                usage = data.get("usage") or {}
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning") or msg.get("reasoning_content")
                if not reasoning and "<think>" in content:
                    reasoning, content = _split_think(content)
                return ChatResponse(
                    content=content,
                    reasoning=reasoning,
                    model=data.get("model", self.model),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    latency_s=time.time() - t0,
                )
            except (httpx.HTTPError, KeyError, ValueError) as e:
                last_err = e
                log.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, self.retries, e)
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"LLM call failed after {self.retries} attempts: {last_err}")


def _split_think(text: str) -> tuple[str, str]:
    start = text.find("<think>")
    end = text.find("</think>")
    if start == -1 or end == -1:
        return "", text
    return text[start + len("<think>") : end].strip(), text[end + len("</think>") :].strip()


def extract_code_block(text: str, lang: str = "lean") -> str:
    """Return the first fenced code block (preferring ```lean), or the raw text."""
    import re

    m = re.search(rf"```{lang}\s*\n(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    return text.strip()


def extract_json(text: str) -> str:
    """Return the first JSON object/array found in text (handles ```json fences)."""
    import re

    m = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    text = text.strip()
    # find outermost { } or [ ]
    for open_c, close_c in (("{", "}"), ("[", "]")):
        s = text.find(open_c)
        e = text.rfind(close_c)
        if s != -1 and e > s:
            return text[s : e + 1]
    return text
