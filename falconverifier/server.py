"""FastAPI server: SSE stream of the verify-and-teach loop + the demo web UI."""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
from collections import defaultdict, deque
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from .agent import VerifyAndTeachAgent
from .config import PROVIDER_PRESETS, Settings
from .lean_runner import LeanRunner
from .memory import memory_from_env

STATIC_DIR = Path(__file__).parent / "static"  # built web app (see web/)
REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH_RESULTS = REPO_ROOT / "bench" / "results"


def _github_blob_base() -> str:
    """`https://github.com/<owner>/<repo>/blob/<ref>` for linking evidence files; env overrides."""
    explicit = os.getenv("FV_GITHUB_BLOB_BASE")
    if explicit:
        return explicit.rstrip("/")
    repo = os.getenv("FV_GITHUB_REPO", "hw4375-collab/FalconVerifer")
    ref = os.getenv("FV_GITHUB_REF", "")
    if not ref:
        try:
            ref = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=5,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            ref = ""
    if not ref or ref == "HEAD":
        ref = "main"
    return f"https://github.com/{repo}/blob/{ref}"


GITHUB_BLOB_BASE = _github_blob_base()
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")

app = FastAPI(title="FalconVerifier", version="0.1.0")

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
    verify: bool = True  # False = raw Falcon baseline, nothing sent to Lean
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


_memory = memory_from_env(Settings.from_env().runs_dir)


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
                agent = VerifyAndTeachAgent(
                    settings, on_event=lambda k, p: q.put((k, p)), memory=_memory
                )
                trace = agent.run(
                    req.problem,
                    expected_answer=req.expected,
                    max_rounds=req.rounds,
                    check=req.verify,
                )
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
        agent = VerifyAndTeachAgent(settings, memory=_memory)
        trace = agent.run(
            req.problem,
            expected_answer=req.expected,
            max_rounds=req.rounds,
            check=req.verify,
        )
        agent.save_trace(trace)
    return JSONResponse(trace.model_dump())


@app.post("/api/check")
def check(req: CheckRequest, request: Request) -> JSONResponse:
    if len(req.props) > 50:
        raise HTTPException(413, "at most 50 propositions per call")
    _gate(request, "\n".join(req.props), None)
    settings = Settings.from_env()
    runner = LeanRunner(settings.lean_project_dir, settings.lean_timeout, memory=_memory)
    with _slots:
        res = runner.check_claims({f"c{i}": p for i, p in enumerate(req.props)})
    return JSONResponse(
        {
            "results": [
                {
                    "prop": p,
                    "verdict": res.outcomes[f"c{i}"].verdict.value,
                    "detail": res.outcomes[f"c{i}"].detail,
                    "cached": res.outcomes[f"c{i}"].cached,
                }
                for i, p in enumerate(req.props)
            ],
            "lean_latency_s": res.latency_s,
            "cache_hits": res.cache_hits,
        }
    )


@app.get("/api/memory")
def memory_stats() -> JSONResponse:
    """What the verifier remembers: kernel verdicts, formalizations and problems seen."""
    if _memory is None:
        return JSONResponse({"enabled": False})
    return JSONResponse({"enabled": True, **_memory.summary()})


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


_runs_cache: dict[str, Any] = {"key": None, "payload": None}
_runs_lock = threading.Lock()


def _latest_results() -> list[Path]:
    if not BENCH_RESULTS.exists():
        return []
    out = []
    for sub in sorted(BENCH_RESULTS.iterdir()):
        runs = sorted(sub.glob("run_*/results.json"))
        if runs:
            out.append(runs[-1])
    return out


@app.get("/api/bench/runs")
def bench_runs() -> JSONResponse:
    """Latest full results (summary + per-problem rows) per results sub-directory, with
    GitHub links to the dataset, the results file and every assurance trace. Cached until
    any results.json changes on disk."""
    latest = _latest_results()
    key = tuple((p.as_posix(), p.stat().st_mtime_ns) for p in latest)
    with _runs_lock:
        if _runs_cache["key"] == key:
            return JSONResponse(_runs_cache["payload"])
        payload = _build_runs_payload(latest)
        _runs_cache.update(key=key, payload=payload)
    return JSONResponse(payload)


def _build_runs_payload(latest: list[Path]) -> dict[str, Any]:
    out: dict[str, Any] = {"github": GITHUB_BLOB_BASE, "runs": {}}
    for rp in latest:
        sub = rp.parent.parent
        data = json.loads(rp.read_text())
        rel_run = rp.parent.relative_to(REPO_ROOT).as_posix()
        problems: dict[str, str] = {}
        ds = REPO_ROOT / str(data.get("dataset", ""))
        if ds.is_file() and ds.suffix == ".jsonl":
            for line in ds.read_text().splitlines():
                if line.strip():
                    item = json.loads(line)
                    problems[item["id"]] = item["problem"]
        out["runs"][sub.name] = {
            "problems": problems,
            "run": rp.parent.name,
            "dataset": data.get("dataset"),
            "student_model": data.get("student_model"),
            "formalizer_model": data.get("formalizer_model"),
            "max_rounds": data.get("max_rounds"),
            "wall_time_s": data.get("wall_time_s"),
            "summary": data.get("summary"),
            "rows": data.get("rows", []),
            "paths": {"results": f"{rel_run}/results.json", "traces": rel_run},
        }
    return out


@app.get("/api/bench/hardness")
def bench_hardness() -> JSONResponse:
    """Per problem text: how often the weak (3B) student got round 1 wrong across every
    committed run, plus the most recent trace of it. Drives the example badges in the UI."""
    latest = _latest_results()
    key = ("hardness", tuple((p.as_posix(), p.stat().st_mtime_ns) for p in latest))
    with _runs_lock:
        if _runs_cache.get("hardness_key") == key:
            return JSONResponse(_runs_cache["hardness"])
        out: dict[str, dict[str, Any]] = {}
        for rp in sorted(BENCH_RESULTS.glob("*/run_*/results.json")):
            data = json.loads(rp.read_text())
            if "3b" not in str(data.get("student_model", "")).lower():
                continue
            ds = REPO_ROOT / str(data.get("dataset", ""))
            if not ds.is_file():
                continue
            text_of = {}
            for line in ds.read_text().splitlines():
                if line.strip():
                    item = json.loads(line)
                    text_of[item["id"]] = item["problem"]
            rel_run = rp.parent.relative_to(BENCH_RESULTS).as_posix()
            for row in data.get("rows", []):
                if row.get("error") or row["id"] not in text_of:
                    continue
                h = out.setdefault(
                    text_of[row["id"]], {"wrong": 0, "total": 0, "expected": row.get("expected")}
                )
                h["total"] += 1
                h["wrong"] += 0 if row.get("baseline_correct") else 1
                if not row.get("baseline_correct") and row.get("final_correct"):
                    h["fixed_trace"] = f"{rel_run}/{row['id']}"
                h["trace"] = f"{rel_run}/{row['id']}"
        _runs_cache.update(hardness_key=key, hardness=out)
    return JSONResponse(out)


@app.get("/api/bench/trace/{sub}/{run}/{problem_id}")
def bench_trace(sub: str, run: str, problem_id: str) -> FileResponse:
    """One assurance trace from a benchmark run (the same JSON that is committed to GitHub)."""
    if not all(_SAFE_NAME.match(x) for x in (sub, run, problem_id)):
        raise HTTPException(400, "bad path")
    path = BENCH_RESULTS / sub / run / f"{problem_id}.json"
    if not path.is_file():
        raise HTTPException(404, "trace not found")
    return FileResponse(path, media_type="application/json")


@app.get("/{path:path}", include_in_schema=False)
def web_app(path: str) -> FileResponse:
    """The web app built from web/ into static/: a built file by path, any other route -> index.html
    (client-side routing: /, /demo, /results). Declared last so /api/* and /healthz win."""
    if path.startswith("api/"):
        raise HTTPException(404, "not found")
    root = STATIC_DIR.resolve()
    target = (STATIC_DIR / path).resolve()
    if path and target.is_file() and target.is_relative_to(root):
        return FileResponse(target)
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(404, "web app not built: run `npm run build` in web/")
    return FileResponse(index)
