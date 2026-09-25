"""FastAPI server: SSE stream of the verify-and-teach loop + a single-page demo UI."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
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

# Deployment knobs: Lean is CPU/RAM heavy, so bound how many loops run at once; bound how
# many solves a single client may start per hour; optional shared token for the API.
MAX_CONCURRENT = int(os.getenv("FV_MAX_CONCURRENT", "2"))
RATE_PER_HOUR = int(os.getenv("FV_RATE_PER_HOUR", "30"))
MAX_PROBLEM_CHARS = int(os.getenv("FV_MAX_PROBLEM_CHARS", "1500"))
ACCESS_TOKEN = os.getenv("FV_ACCESS_TOKEN", "")
_slots = threading.BoundedSemaphore(MAX_CONCURRENT)
_hits: dict[str, deque[float]] = defaultdict(deque)
_hits_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def _gate(request: Request, problem: str, rounds: int | None) -> None:
    if ACCESS_TOKEN and request.headers.get("x-fv-token", "") != ACCESS_TOKEN:
        raise HTTPException(401, "missing or invalid X-FV-Token")
    if not problem.strip():
        raise HTTPException(422, "empty problem")
    if len(problem) > MAX_PROBLEM_CHARS:
        raise HTTPException(413, f"problem longer than {MAX_PROBLEM_CHARS} characters")
    if rounds is not None and not 1 <= rounds <= 5:
        raise HTTPException(422, "rounds must be between 1 and 5")
    ip, now = _client_ip(request), time.time()
    with _hits_lock:
        h = _hits[ip]
        while h and now - h[0] > 3600:
            h.popleft()
        if len(h) >= RATE_PER_HOUR:
            raise HTTPException(429, "rate limit: try again later")
        h.append(now)


class SolveRequest(BaseModel):
    problem: str
    expected: str | None = None
    rounds: int | None = None
    formalizer: str | None = None  # falcon | openai | openrouter
    student_model: str | None = None


class CheckRequest(BaseModel):
    props: list[str]


ALLOWED_STUDENTS = {
    m.strip()
    for m in os.getenv(
        "FV_STUDENT_MODELS",
        "falcon-h1-7b-instruct,falcon-h1-arabic-3b-instruct,falcon-h1r-7b",
    ).split(",")
    if m.strip()
}


def _settings(req: SolveRequest) -> Settings:
    provider = req.formalizer if req.formalizer in PROVIDER_PRESETS else None
    s = Settings.from_env(provider)
    if req.student_model:
        if req.student_model not in ALLOWED_STUDENTS:
            raise HTTPException(422, f"unknown student model {req.student_model!r}")
        s.student.model = req.student_model
    return s


def _sse(kind: str, payload: dict[str, Any]) -> str:
    return f"event: {kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _run_stream(req: SolveRequest) -> Iterator[str]:
    q: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()
    settings = _settings(req)

    def worker() -> None:
        try:
            if not _slots.acquire(timeout=float(os.getenv("FV_QUEUE_WAIT_S", "600"))):
                q.put(("error", {"message": "server busy: all Lean workers are taken, retry"}))
                return
            try:
                agent = VerifyAndTeachAgent(settings, on_event=lambda k, p: q.put((k, p)))
                trace = agent.run(req.problem, expected_answer=req.expected, max_rounds=req.rounds)
                path = agent.save_trace(trace)
                q.put(("saved", {"path": str(path)}))
            finally:
                _slots.release()
        except Exception as e:  # surface errors to the UI instead of a dead stream
            q.put(("error", {"message": f"{type(e).__name__}: {e}"}))
        finally:
            q.put(None)

    threading.Thread(target=worker, daemon=True).start()
    yield _sse(
        "config",
        {"student": settings.student.model, "formalizer": settings.formalizer.model},
    )
    if _slots._value == 0:
        yield _sse("status", {"message": "queued: waiting for a free Lean worker"})
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


@app.get("/healthz")
def healthz() -> JSONResponse:
    s = Settings.from_env()
    lean_ok = (s.lean_project_dir / ".lake").exists()
    return JSONResponse(
        {
            "ok": lean_ok and bool(s.student.api_key),
            "lean_project": lean_ok,
            "falcon_key": bool(s.student.api_key),
            "free_workers": _slots._value,
            "max_concurrent": MAX_CONCURRENT,
        }
    )


@app.post("/api/solve/stream")
def solve_stream(req: SolveRequest, request: Request) -> StreamingResponse:
    _gate(request, req.problem, req.rounds)
    return StreamingResponse(
        _run_stream(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/solve")
def solve(req: SolveRequest, request: Request) -> JSONResponse:
    _gate(request, req.problem, req.rounds)
    settings = _settings(req)
    with _slots:
        agent = VerifyAndTeachAgent(settings)
        trace = agent.run(req.problem, expected_answer=req.expected, max_rounds=req.rounds)
    return JSONResponse(trace.model_dump())


@app.post("/api/check")
def check(req: CheckRequest, request: Request) -> JSONResponse:
    if len(req.props) > 50:
        raise HTTPException(413, "at most 50 propositions per call")
    _gate(request, "\n".join(req.props), None)
    settings = Settings.from_env()
    runner = LeanRunner(settings.lean_project_dir, settings.lean_timeout)
    with _slots:
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
