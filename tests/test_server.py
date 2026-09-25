"""Deployment guards of the FastAPI server (no Falcon / Lean calls)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from falconverifier import server


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(server, "ACCESS_TOKEN", "")
    monkeypatch.setattr(server, "RATE_PER_HOUR", 3)
    server._hits.clear()
    return TestClient(server.app)


def test_healthz_reports_lean_and_key(client):
    body = client.get("/healthz").json()
    assert {"ok", "lean_project", "falcon_key", "free_workers", "max_concurrent"} <= body.keys()
    assert body["free_workers"] == server.MAX_CONCURRENT


def test_rejects_empty_oversized_and_bad_rounds(client, monkeypatch):
    monkeypatch.setattr(server, "MAX_PROBLEM_CHARS", 20)
    assert client.post("/api/solve", json={"problem": "   "}).status_code == 422
    assert client.post("/api/solve", json={"problem": "x" * 21}).status_code == 413
    assert client.post("/api/solve", json={"problem": "2+2", "rounds": 9}).status_code == 422


def test_unknown_student_model_rejected(client):
    r = client.post("/api/solve", json={"problem": "2+2", "student_model": "gpt-4"})
    assert r.status_code == 422
    assert "unknown student model" in r.json()["detail"]


def test_access_token_required_when_configured(client, monkeypatch):
    monkeypatch.setattr(server, "ACCESS_TOKEN", "s3cret")
    assert client.post("/api/solve", json={"problem": "x" * 2000}).status_code == 401
    r = client.post("/api/solve", json={"problem": "x" * 2000}, headers={"X-FV-Token": "s3cret"})
    assert r.status_code == 413  # authenticated -> next gate fires


def test_rate_limit_per_client(client):
    body = {"problem": "2+2", "student_model": "not-a-model"}  # passes _gate, fails later
    for _ in range(3):
        assert client.post("/api/solve", json=body).status_code == 422
    assert client.post("/api/solve", json=body).status_code == 429


def test_formalizer_choice_does_not_mutate_process_env(client, monkeypatch):
    monkeypatch.delenv("FORMALIZER_PROVIDER", raising=False)
    s = server._settings(server.SolveRequest(problem="p", formalizer="openai"))
    assert s.formalizer.model == server.PROVIDER_PRESETS["openai"]["model"]
    import os

    assert "FORMALIZER_PROVIDER" not in os.environ


def test_pages_served(client):
    for path in ("/", "/benchmark", "/about"):
        r = client.get(path)
        assert r.status_code == 200 and "ChaosButterfly" in r.text


def test_bench_runs_payload_links_to_evidence(client):
    data = client.get("/api/bench/runs").json()
    assert data["github"].startswith("https://github.com/")
    for run in data["runs"].values():
        assert run["paths"]["results"].endswith("/results.json")
        assert run["paths"]["traces"].startswith("bench/results/")
        assert "all" in run["summary"]
        assert all(r["id"] in run["problems"] for r in run["rows"] if not r.get("error"))


def test_bench_runs_is_cached(client, monkeypatch):
    client.get("/api/bench/runs")
    calls = []
    monkeypatch.setattr(server, "_build_runs_payload", lambda latest: calls.append(1) or {})
    client.get("/api/bench/runs")
    assert calls == []


def test_bench_trace_rejects_path_traversal(client):
    assert client.get("/api/bench/trace/..%2F..%2Fetc/x/passwd").status_code in (400, 404)
    assert client.get("/api/bench/trace/falcon3b_arabic/run_x/nope").status_code == 404
    data = client.get("/api/bench/runs").json()
    if "falcon3b_arabic" in data["runs"]:
        run = data["runs"]["falcon3b_arabic"]
        pid = run["rows"][0]["id"]
        t = client.get(f"/api/bench/trace/falcon3b_arabic/{run['run']}/{pid}").json()
        assert t["problem"] == run["problems"][pid] and t["rounds"]
