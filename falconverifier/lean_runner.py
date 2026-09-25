from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .memory import Memory, env_fingerprint
from .schemas import LeanDiagnostic, Verdict

log = logging.getLogger(__name__)

# Tactic cascade: each alternative must fully close the goal (`done`), otherwise `first`
# moves on. Covers arithmetic (norm_num/omega/ring), inequalities (linarith/nlinarith),
# finite-model logic (decide over Fin n -> Bool), and propositional logic (tauto).
_WITNESSES_1 = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 21)
_WITNESSES_2 = ((0, 0), (0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2), (2, 15), (3, 10), (5, 6))
_CLOSERS = ("norm_num", "omega", "decide")
_DEGREES = range(1, 10)

# Regular-graph claims (`FalconVerifier.Regular`, see lean/FalconVerifier/Graph.lean) get their
# own cascade: the handshake lemma for impossibility, an explicit circulant witness for
# existence, and *no* generic `decide` — on `∃ f : Fin n → Fin n → Bool, …` it would enumerate
# 2^(n²) relations and die with an unrecoverable max-recursion error.
_FV_GRAPH_ALTERNATIVES = [
    "exact FalconVerifier.no_regular_of_odd (by decide)",
    "exact FalconVerifier.not_regular_of_odd (by decide)",
    "push Not; exact FalconVerifier.no_regular_of_odd (by decide)",
    "push Not; exact FalconVerifier.not_regular_of_odd (by decide)",
    "exact FalconVerifier.not_regular_of_ge (by decide)",
    "exact FalconVerifier.no_regular_of_ge (by decide)",
    "push Not; exact FalconVerifier.no_regular_of_ge (by decide)",
    "push Not; exact FalconVerifier.not_regular_of_ge (by decide)",
    *(f"exact ⟨FalconVerifier.circulant _ {k}, by decide⟩" for k in _DEGREES),
    *(f"push Not; exact ⟨FalconVerifier.circulant _ {k}, by decide⟩" for k in _DEGREES),
]
_GRAPH_CLAIM = re.compile(r"FalconVerifier\.(Regular|IsGraph|degree)\b")

_FV_ALTERNATIVES = [
    "decide",
    "norm_num",
    "omega",
    "simp",
    "rfl",
    "intros; tauto",
    "intros; omega",
    "intros; linarith",
    "intros; simp_all",
    "intros; norm_num at *",
    "intros; simp_all; omega",
    "intros; simp_all; linarith",
    "intros; simp_all; nlinarith",
    "intros; aesop",
    "ring_nf",
    "norm_num; ring_nf",
    "field_simp; ring_nf",
    "positivity",
    "intros; decide",
    "intros; simp_all; decide",
    "simp; decide",
    "push Not; intros; simp_all; decide",
    "push Not; norm_num",
    "push Not; decide",
    "push Not; intros; simp_all",
    "push Not; intros; simp_all; omega",
    "push Not; intros; simp_all; linarith",
    "push Not; intros; aesop",
    # counterexample search for refuting `∀ n, …` / `∀ a b, …` over small literals
    *(f"push Not; refine ⟨{k}, ?_⟩; {t}" for k in _WITNESSES_1 for t in _CLOSERS),
    *(f"push Not; refine ⟨{a}, {b}, ?_⟩; {t}" for a, b in _WITNESSES_2 for t in _CLOSERS),
    "intro x; nlinarith [mul_self_nonneg x, sq_nonneg x]",
    "intro x; nlinarith [sq_nonneg (x - 1), sq_nonneg (x + 1)]",
    "rintro ⟨x, hx⟩; nlinarith [mul_self_nonneg x, sq_nonneg x]",
    "intro x; intro hx; nlinarith [mul_self_nonneg x, sq_nonneg x]",
    # last: bare nlinarith can *log* (not throw) an error on ∀-hypotheses, which `first`
    # cannot backtrack from, so nothing may come after it
    "intros; nlinarith",
]


def _macro(name: str, alternatives: list[str]) -> str:
    return (
        f'macro "{name}" : tactic => `(tactic| first\n'
        + "\n".join(f"  | ({alt}; done)" for alt in alternatives)
        + ")\n"
    )


FV_AUTO_MACRO = _macro("fv_auto", _FV_ALTERNATIVES) + _macro("fv_graph", _FV_GRAPH_ALTERNATIVES)

HEADER = (
    "import Mathlib\n"
    "import FalconVerifier.Graph\n"
    "set_option maxHeartbeats 400000\n"
    "set_option linter.all false\n"
    "set_option autoImplicit false\n\n"
)


@dataclass
class ClaimOutcome:
    verdict: Verdict
    detail: str
    cached: bool = False


@dataclass
class LeanRunResult:
    outcomes: dict[str, ClaimOutcome]
    diagnostics: list[LeanDiagnostic]
    source: str
    latency_s: float
    cache_hits: int = 0


class LeanRunner:
    """Compiles a batch of claims with Lean 4 + Mathlib and classifies each one.

    For every claim `P` we emit three declarations on three known lines:
        theorem <id>_wf  : P   := by sorry     -- does P even type-check?
        theorem <id>_pos : P   := by fv_auto   -- can automation prove P?
        theorem <id>_neg : ¬(P) := by fv_auto  -- can automation prove ¬P?
    and map the compiler diagnostics back by line number.
    """

    def __init__(self, project_dir: Path, timeout: float = 120.0, memory: Memory | None = None):
        self.project_dir = Path(project_dir).resolve()
        self.timeout = timeout
        self.scratch = self.project_dir / "scratch"
        self.scratch.mkdir(exist_ok=True)
        self.memory = memory
        self.env_id = env_fingerprint(self.project_dir, HEADER + FV_AUTO_MACRO) if memory else ""

    # -- public API -----------------------------------------------------------------

    def check_claims(self, claims: dict[str, str]) -> LeanRunResult:
        """claims: id -> Lean Prop source (single expression)."""
        if not claims:
            return LeanRunResult({}, [], "", 0.0)
        outcomes: dict[str, ClaimOutcome] = {}
        remembered: dict[str, str] = {}
        if self.memory is not None:
            for cid, prop in claims.items():
                hit = self.memory.get_verdict(self.env_id, prop, _tactic_for(prop))
                if hit is not None:
                    when = time.strftime("%Y-%m-%d", time.gmtime(hit.created_at))
                    note = f"kernel verdict from memory (first decided {when}, hit #{hit.hits})"
                    outcomes[cid] = ClaimOutcome(
                        hit.verdict, f"{hit.detail} · {note}" if hit.detail else note, True
                    )
                    remembered[cid] = " ".join(prop.split())
        fresh = {cid: p for cid, p in claims.items() if cid not in outcomes}
        if not fresh:
            return LeanRunResult(outcomes, [], _memory_note(remembered), 0.0, len(remembered))
        source, line_map = self._build_source(fresh)
        t0 = time.time()
        diags = self._compile(source)
        latency = time.time() - t0
        source += _memory_note(remembered)
        claims = fresh

        errors_by_line: dict[int, list[str]] = {}
        for d in diags:
            if d.severity == "error":
                errors_by_line.setdefault(d.line, []).append(d.message)

        if 0 in errors_by_line:  # global failure (timeout / crash): nothing is decided
            detail = _first_line(errors_by_line[0][0])
            outcomes.update({cid: ClaimOutcome(Verdict.UNKNOWN, detail) for cid in claims})
            return LeanRunResult(outcomes, diags, source, latency, len(remembered))
        for cid in claims:
            wf_line, pos_line, neg_line = line_map[cid]
            wf_err = errors_by_line.get(wf_line)
            if wf_err:
                outcomes[cid] = ClaimOutcome(Verdict.ILL_FORMED, _first_line(wf_err[0]))
                continue
            pos_ok = pos_line not in errors_by_line
            neg_ok = neg_line not in errors_by_line
            if pos_ok and not neg_ok:
                outcomes[cid] = ClaimOutcome(Verdict.VERIFIED, "")
            elif neg_ok and not pos_ok:
                outcomes[cid] = ClaimOutcome(
                    Verdict.REFUTED, _refutation_detail(errors_by_line.get(pos_line, []))
                )
            elif pos_ok and neg_ok:  # inconsistent: should never happen, treat as unknown
                outcomes[cid] = ClaimOutcome(Verdict.UNKNOWN, "both P and ¬P proved?!")
            else:
                outcomes[cid] = ClaimOutcome(
                    Verdict.UNKNOWN, _first_line(errors_by_line.get(pos_line, [""])[0])
                )
        if self.memory is not None:
            for cid, prop in claims.items():
                o = outcomes[cid]
                self.memory.put_verdict(self.env_id, prop, _tactic_for(prop), o.verdict, o.detail)
        return LeanRunResult(outcomes, diags, source, latency, len(remembered))

    def compile_snippet(self, body: str) -> list[LeanDiagnostic]:
        return self._compile(HEADER + body)

    # -- internals ------------------------------------------------------------------

    def _build_source(self, claims: dict[str, str]) -> tuple[str, dict[str, tuple[int, int, int]]]:
        lines = (HEADER + FV_AUTO_MACRO).split("\n")
        # HEADER ends with blank line; FV_AUTO_MACRO ends with "\n" so last elem is "".
        line_map: dict[str, tuple[int, int, int]] = {}
        for cid, prop in claims.items():
            p = " ".join(prop.split())  # one physical line per declaration
            lines.append("")
            start = len(lines) + 1  # 1-based line number of the next appended line
            tac = _tactic_for(p)
            lines.append(f"theorem {cid}_wf : {p} := by sorry")
            lines.append(f"theorem {cid}_pos : {p} := by {tac}")
            lines.append(f"theorem {cid}_neg : ¬ ({p}) := by {tac}")
            line_map[cid] = (start, start + 1, start + 2)
        return "\n".join(lines) + "\n", line_map

    def _compile(self, source: str) -> list[LeanDiagnostic]:
        path = self.scratch / f"fv_{uuid.uuid4().hex[:10]}.lean"
        path.write_text(source)
        env = dict(os.environ)
        elan_bin = Path.home() / ".elan" / "bin"
        if elan_bin.exists():
            env["PATH"] = f"{elan_bin}:{env.get('PATH', '')}"
        try:
            proc = subprocess.run(
                ["lake", "env", "lean", "--json", str(path)],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            log.error("Lean timed out after %ss", self.timeout)
            return [LeanDiagnostic(line=0, severity="error", message="lean timeout")]
        finally:
            try:
                path.unlink()
            except OSError:
                pass
        diags: list[LeanDiagnostic] = []
        for raw in proc.stdout.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                diags.append(LeanDiagnostic(line=0, severity="error", message=raw))
                continue
            diags.append(
                LeanDiagnostic(
                    line=int(d.get("pos", {}).get("line", 0)),
                    severity=d.get("severity", "error"),
                    message=d.get("data", ""),
                )
            )
        if proc.returncode != 0 and not diags:
            diags.append(
                LeanDiagnostic(line=0, severity="error", message=proc.stderr.strip()[:2000])
            )
        return diags


def _tactic_for(prop: str) -> str:
    return "fv_graph" if _GRAPH_CLAIM.search(prop) else "fv_auto"


def _memory_note(remembered: dict[str, str]) -> str:
    if not remembered:
        return ""
    lines = ["", "-- claims below were not recompiled: verdicts served from kernel memory"]
    lines += [f"-- {cid} : {p}" for cid, p in remembered.items()]
    return "\n".join(lines) + "\n"


def _first_line(msg: str) -> str:
    return msg.strip().split("\n")[0][:300]


def _refutation_detail(pos_errors: list[str]) -> str:
    for m in pos_errors:
        if "proved that the proposition" in m:
            return " ".join(m.split())[:300]
    return "Lean proved the negation of this claim."
