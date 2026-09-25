"""Persistent memory for the deterministic parts of the verification loop.

Falcon's answers are sampled, so a repeated question can never be answered from memory
without breaking the assurance semantics. What *is* reusable is everything downstream of
the text that is decided deterministically:

* ``lean``   – kernel verdicts.  The same Lean proposition checked with the same tactic
  under the same toolchain/Mathlib/prelude fingerprint always yields the same verdict, so
  ``verified``/``refuted``/``ill_formed`` outcomes are stored forever (``unknown`` is not:
  it may be a timeout).
* ``formal`` – LLM formalizations.  ``(formalizer model, problem, step text)`` ->
  Lean proposition, stored only after the proposition type-checked.
* ``problem`` – problems seen before: their normalized text, expected answer, last status
  and the trace files, so a repeated question is recognised and its history is linked.

Everything is keyed by a SHA-256 of normalized text; Eastern Arabic digits, whitespace and
Arabic diacritics/tatweel are normalized so «٥» and «5» share an entry.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schemas import Verdict

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")
_WS = re.compile(r"\s+")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS lean_claims (
    key TEXT PRIMARY KEY,
    env TEXT NOT NULL,
    prop TEXT NOT NULL,
    tactic TEXT NOT NULL,
    verdict TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at REAL NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS formalizations (
    key TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    problem TEXT NOT NULL,
    text TEXT NOT NULL,
    lean_prop TEXT,
    kind TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at REAL NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS problems (
    key TEXT PRIMARY KEY,
    problem TEXT NOT NULL,
    expected_answer TEXT,
    last_status TEXT,
    last_final_answer TEXT,
    traces TEXT NOT NULL,
    seen INTEGER NOT NULL DEFAULT 0,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL
);
"""

DECISIVE = {Verdict.VERIFIED, Verdict.REFUTED, Verdict.ILL_FORMED}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_ARABIC_DIGITS)
    text = _DIACRITICS.sub("", text)
    return _WS.sub(" ", text).strip()


def _key(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def env_fingerprint(project_dir: Path, header: str) -> str:
    """Hash of everything a kernel verdict depends on besides the proposition itself."""
    h = hashlib.sha256(header.encode("utf-8"))
    for rel in ("lean-toolchain", "lake-manifest.json", "lakefile.toml"):
        p = project_dir / rel
        if p.exists():
            h.update(p.read_bytes())
    src = project_dir / "FalconVerifier"
    for p in sorted(src.rglob("*.lean")) if src.exists() else []:
        h.update(p.relative_to(project_dir).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


@dataclass
class CachedVerdict:
    verdict: Verdict
    detail: str
    created_at: float
    hits: int


@dataclass
class CachedFormalization:
    lean_prop: str | None
    kind: str
    note: str


@dataclass
class ProblemRecord:
    problem: str
    expected_answer: str | None
    last_status: str | None
    last_final_answer: str | None
    traces: list[str]
    seen: int
    first_seen: float
    last_seen: float


class Memory:
    """SQLite-backed store; one connection per call so it is safe across server threads."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.stats: dict[str, int] = {
            "lean_hits": 0,
            "lean_misses": 0,
            "formal_hits": 0,
            "formal_misses": 0,
        }
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30)
        c.execute("PRAGMA journal_mode=WAL")
        return c

    # -- Lean verdicts -----------------------------------------------------------------

    @staticmethod
    def lean_key(env: str, prop: str, tactic: str) -> str:
        return _key("lean", env, " ".join(prop.split()), tactic)

    def get_verdict(self, env: str, prop: str, tactic: str) -> CachedVerdict | None:
        k = self.lean_key(env, prop, tactic)
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT verdict, detail, created_at, hits FROM lean_claims WHERE key=?", (k,)
            ).fetchone()
            if row is None:
                self.stats["lean_misses"] += 1
                return None
            c.execute("UPDATE lean_claims SET hits=hits+1 WHERE key=?", (k,))
            self.stats["lean_hits"] += 1
        return CachedVerdict(Verdict(row[0]), row[1], row[2], row[3] + 1)

    def put_verdict(self, env: str, prop: str, tactic: str, verdict: Verdict, detail: str) -> None:
        if verdict not in DECISIVE:
            return
        k = self.lean_key(env, prop, tactic)
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT OR IGNORE INTO lean_claims VALUES (?,?,?,?,?,?,?,0)",
                (k, env, " ".join(prop.split()), tactic, verdict.value, detail, time.time()),
            )

    # -- LLM formalizations --------------------------------------------------------------

    @staticmethod
    def formal_key(model: str, problem: str, text: str) -> str:
        return _key("formal", model, normalize(problem), normalize(text))

    def get_formalization(self, model: str, problem: str, text: str) -> CachedFormalization | None:
        k = self.formal_key(model, problem, text)
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT lean_prop, kind, note FROM formalizations WHERE key=?", (k,)
            ).fetchone()
            if row is None:
                self.stats["formal_misses"] += 1
                return None
            c.execute("UPDATE formalizations SET hits=hits+1 WHERE key=?", (k,))
            self.stats["formal_hits"] += 1
        return CachedFormalization(row[0], row[1], row[2])

    def put_formalization(
        self, model: str, problem: str, text: str, lean_prop: str | None, kind: str, note: str
    ) -> None:
        k = self.formal_key(model, problem, text)
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO formalizations VALUES (?,?,?,?,?,?,?,?,0)",
                (k, model, normalize(problem), normalize(text), lean_prop, kind, note, time.time()),
            )

    # -- problems ------------------------------------------------------------------------

    @staticmethod
    def problem_key(problem: str) -> str:
        return _key("problem", normalize(problem))

    def get_problem(self, problem: str) -> ProblemRecord | None:
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT problem, expected_answer, last_status, last_final_answer, traces, seen,"
                " first_seen, last_seen FROM problems WHERE key=?",
                (self.problem_key(problem),),
            ).fetchone()
        if row is None:
            return None
        return ProblemRecord(
            row[0], row[1], row[2], row[3], json.loads(row[4]), row[5], row[6], row[7]
        )

    def remember_problem(
        self,
        problem: str,
        expected_answer: str | None,
        status: str,
        final_answer: str | None,
        trace_path: str | None,
    ) -> ProblemRecord:
        k = self.problem_key(problem)
        now = time.time()
        with self._lock, self._conn() as c:
            row = c.execute(
                "SELECT expected_answer, traces, seen, first_seen FROM problems WHERE key=?", (k,)
            ).fetchone()
            if row is None:
                traces = [trace_path] if trace_path else []
                c.execute(
                    "INSERT INTO problems VALUES (?,?,?,?,?,?,1,?,?)",
                    (
                        k,
                        problem,
                        expected_answer,
                        status,
                        final_answer,
                        json.dumps(traces),
                        now,
                        now,
                    ),
                )
                seen, first = 1, now
            else:
                traces = json.loads(row[1])
                if trace_path:
                    traces = (traces + [trace_path])[-20:]
                expected_answer = expected_answer or row[0]
                seen, first = row[2] + 1, row[3]
                c.execute(
                    "UPDATE problems SET expected_answer=?, last_status=?, last_final_answer=?,"
                    " traces=?, seen=?, last_seen=? WHERE key=?",
                    (expected_answer, status, final_answer, json.dumps(traces), seen, now, k),
                )
        return ProblemRecord(
            problem, expected_answer, status, final_answer, traces, seen, first, now
        )

    # -- introspection -----------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        with self._lock, self._conn() as c:
            lean_n, lean_hits = c.execute(
                "SELECT COUNT(*), COALESCE(SUM(hits),0) FROM lean_claims"
            ).fetchone()
            by_verdict = dict(
                c.execute("SELECT verdict, COUNT(*) FROM lean_claims GROUP BY verdict").fetchall()
            )
            formal_n, formal_hits = c.execute(
                "SELECT COUNT(*), COALESCE(SUM(hits),0) FROM formalizations"
            ).fetchone()
            prob_n, prob_seen = c.execute(
                "SELECT COUNT(*), COALESCE(SUM(seen),0) FROM problems"
            ).fetchone()
        return {
            "path": str(self.path),
            "lean_claims": {"stored": lean_n, "hits": lean_hits, "by_verdict": by_verdict},
            "formalizations": {"stored": formal_n, "hits": formal_hits},
            "problems": {"stored": prob_n, "asked": prob_seen},
            "session": dict(self.stats),
        }


def memory_from_env(default_dir: Path) -> Memory | None:
    """``FV_MEMORY=0`` disables memory; ``FV_MEMORY_PATH`` relocates the database."""
    if os.getenv("FV_MEMORY", "1").lower() in {"0", "false", "no", "off"}:
        return None
    return Memory(Path(os.getenv("FV_MEMORY_PATH", default_dir / "memory.sqlite")))
