from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .schemas import LeanDiagnostic, Verdict

log = logging.getLogger(__name__)

# Tactic cascade: each alternative must fully close the goal (`done`), otherwise `first`
# moves on. Covers arithmetic (norm_num/omega/ring), inequalities (linarith/nlinarith),
# finite-model logic (decide over Fin n -> Bool), and propositional logic (tauto).
_WITNESSES_1 = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 21)
_WITNESSES_2 = ((0, 0), (0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 2), (2, 15), (3, 10), (5, 6))
_CLOSERS = ("norm_num", "omega", "decide")

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
FV_AUTO_MACRO = (
    'macro "fv_auto" : tactic => `(tactic| first\n'
    + "\n".join(f"  | ({alt}; done)" for alt in _FV_ALTERNATIVES)
    + ")\n"
)

HEADER = (
    "import Mathlib\n"
    "set_option maxHeartbeats 400000\n"
    "set_option linter.all false\n"
    "set_option autoImplicit false\n\n"
)


@dataclass
class ClaimOutcome:
    verdict: Verdict
    detail: str


@dataclass
class LeanRunResult:
    outcomes: dict[str, ClaimOutcome]
    diagnostics: list[LeanDiagnostic]
    source: str
    latency_s: float


class LeanRunner:
    """Compiles a batch of claims with Lean 4 + Mathlib and classifies each one.

    For every claim `P` we emit three declarations on three known lines:
        theorem <id>_wf  : P   := by sorry     -- does P even type-check?
        theorem <id>_pos : P   := by fv_auto   -- can automation prove P?
        theorem <id>_neg : ¬(P) := by fv_auto  -- can automation prove ¬P?
    and map the compiler diagnostics back by line number.
    """

    def __init__(self, project_dir: Path, timeout: float = 120.0):
        self.project_dir = Path(project_dir).resolve()
        self.timeout = timeout
        self.scratch = self.project_dir / "scratch"
        self.scratch.mkdir(exist_ok=True)

    # -- public API -----------------------------------------------------------------

    def check_claims(self, claims: dict[str, str]) -> LeanRunResult:
        """claims: id -> Lean Prop source (single expression)."""
        if not claims:
            return LeanRunResult({}, [], "", 0.0)
        source, line_map = self._build_source(claims)
        t0 = time.time()
        diags = self._compile(source)
        latency = time.time() - t0

        errors_by_line: dict[int, list[str]] = {}
        for d in diags:
            if d.severity == "error":
                errors_by_line.setdefault(d.line, []).append(d.message)

        outcomes: dict[str, ClaimOutcome] = {}
        if 0 in errors_by_line:  # global failure (timeout / crash): nothing is decided
            detail = _first_line(errors_by_line[0][0])
            return LeanRunResult(
                {cid: ClaimOutcome(Verdict.UNKNOWN, detail) for cid in claims},
                diags,
                source,
                latency,
            )
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
        return LeanRunResult(outcomes, diags, source, latency)

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
            lines.append(f"theorem {cid}_wf : {p} := by sorry")
            lines.append(f"theorem {cid}_pos : {p} := by fv_auto")
            lines.append(f"theorem {cid}_neg : ¬ ({p}) := by fv_auto")
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


def _first_line(msg: str) -> str:
    return msg.strip().split("\n")[0][:300]


def _refutation_detail(pos_errors: list[str]) -> str:
    for m in pos_errors:
        if "proved that the proposition" in m:
            return " ".join(m.split())[:300]
    return "Lean proved the negation of this claim."
