"""FastAPI server: SSE stream of the verify-and-teach loop + a single-page demo UI."""

from __future__ import annotations

import json
import os
import queue
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .agent import VerifyAndTeachAgent
from .config import PROVIDER_PRESETS, Settings
from .lean_runner import LeanRunner

STATIC_DIR = Path(__file__).parent / "static"
BENCH_RESULTS = Path(__file__).resolve().parent.parent / "bench" / "results"

app = FastAPI(title="FalconVerifier", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SolveRequest(BaseModel):
    problem: str
    expected: str | None = None
    rounds: int | None = None
    formalizer: str | None = None  # falcon | openai | openrouter
    student_model: str | None = None


class CheckRequest(BaseModel):
    props: list[str]


def _settings(req: SolveRequest) -> Settings:
    if req.formalizer and req.formalizer in PROVIDER_PRESETS:
        os.environ["FORMALIZER_PROVIDER"] = req.formalizer
    s = Settings.from_env()
    if req.student_model:
        s.student.model = req.student_model
    return s


def _sse(kind: str, payload: dict[str, Any]) -> str:
    return f"event: {kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _run_stream(req: SolveRequest) -> Iterator[str]:
    q: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()
    settings = _settings(req)

    def worker() -> None:
        try:
            agent = VerifyAndTeachAgent(settings, on_event=lambda k, p: q.put((k, p)))
            trace = agent.run(req.problem, expected_answer=req.expected, max_rounds=req.rounds)
            path = agent.save_trace(trace)
            q.put(("saved", {"path": str(path)}))
        except Exception as e:  # surface errors to the UI instead of a dead stream
            q.put(("error", {"message": f"{type(e).__name__}: {e}"}))
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()
    yield _sse(
        "config",
        {"student": settings.student.model, "formalizer": settings.formalizer.model},
    )
    while True:
        try:
            item = q.get(timeout=15)
        except queue.Empty:
            yield ": keep-alive\n\n"
            continue
        if item is None:
            break
        kind, payload = item
        yield _sse(kind, payload)


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/solve/stream")
def solve_stream(req: SolveRequest) -> StreamingResponse:
    return StreamingResponse(
        _run_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/solve")
def solve(req: SolveRequest) -> JSONResponse:
    settings = _settings(req)
    agent = VerifyAndTeachAgent(settings)
    trace = agent.run(req.problem, expected_answer=req.expected, max_rounds=req.rounds)
    return JSONResponse(trace.model_dump())


@app.post("/api/check")
def check(req: CheckRequest) -> JSONResponse:
    settings = Settings.from_env()
    runner = LeanRunner(settings.lean_project_dir, settings.lean_timeout)
    res = runner.check_claims({f"c{i}": p for i, p in enumerate(req.props)})
    return JSONResponse(
        {
            "results": [
                {
                    "prop": p,
                    "verdict": res.outcomes[f"c{i}"].verdict.value,
                    "detail": res.outcomes[f"c{i}"].detail,
                }
                for i, p in enumerate(req.props)
            ],
            "lean_latency_s": res.latency_s,
        }
    )


@app.get("/api/config")
def config() -> JSONResponse:
    s = Settings.from_env()
    return JSONResponse(
        {
            "student": s.student.model,
            "formalizer": s.formalizer.model,
            "formalizer_provider": os.getenv("FORMALIZER_PROVIDER", "falcon"),
            "providers": {
                k: {"model": v["model"], "configured": bool(os.getenv(v["key_env"]))}
                for k, v in PROVIDER_PRESETS.items()
            },
            "max_rounds": s.max_rounds,
        }
    )


@app.get("/api/bench/latest")
def bench_latest(request: Request) -> JSONResponse:
    """Most recent benchmark summary per results sub-directory (for the dashboard)."""
    out: dict[str, Any] = {}
    if BENCH_RESULTS.exists():
        for sub in sorted(BENCH_RESULTS.iterdir()):
            runs = sorted(sub.glob("run_*/results.json"))
            if runs:
                data = json.loads(runs[-1].read_text())
                out[sub.name] = {"run": runs[-1].parent.name, "summary": data.get("summary")}
    return JSONResponse(out)
