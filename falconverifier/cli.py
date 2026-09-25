from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agent import VerifyAndTeachAgent
from .config import Settings
from .schemas import Verdict

app = typer.Typer(help="FalconVerifier: Lean 4 verify-and-teach loop for Falcon LLMs")
console = Console()

VERDICT_STYLE = {
    Verdict.VERIFIED: "bold green",
    Verdict.REFUTED: "bold red",
    Verdict.UNKNOWN: "yellow",
    Verdict.ILL_FORMED: "magenta",
    Verdict.SKIPPED: "dim",
}


def _settings(formalizer: str | None) -> Settings:
    if formalizer:
        os.environ["FORMALIZER_PROVIDER"] = formalizer
    return Settings.from_env()


def _print_event(kind: str, payload: dict[str, Any]) -> None:
    if kind == "round_start":
        console.rule(f"[bold]Round {payload['round']}/{payload['max_rounds']}")
    elif kind == "student_answer":
        a = payload["answer"]
        if a.get("reasoning"):
            console.print(
                Panel(a["reasoning"][:1500], title="Falcon chain-of-thought", style="dim")
            )
        console.print(Panel(a["raw"], title=f"Falcon answer ({a['latency_s']:.1f}s)"))
    elif kind == "verified":
        rep = payload["report"]
        t = Table(title=f"Lean 4 verification ({rep['lean_latency_s']:.1f}s)")
        t.add_column("Step", justify="right")
        t.add_column("Verdict")
        t.add_column("Lean claim")
        t.add_column("Detail")
        for s in rep["steps"]:
            v = Verdict(s["verdict"])
            t.add_row(
                str(s["index"]),
                f"[{VERDICT_STYLE[v]}]{v.value}[/]",
                (s["lean_prop"] or "-")[:70],
                (s["detail"] or "")[:60],
            )
        fv = Verdict(rep["final_answer_verdict"])
        t.add_row(
            "final", f"[{VERDICT_STYLE[fv]}]{fv.value}[/]", "", rep["final_answer_detail"][:60]
        )
        console.print(t)
    elif kind == "feedback":
        console.print(Panel(payload["feedback"], title="Teaching feedback -> Falcon", style="cyan"))
    elif kind == "repair":
        console.print(f"[magenta]repairing formalization: {payload['errors']}")


@app.command()
def solve(
    problem: str = typer.Argument(..., help="Math or logic problem in natural language"),
    expected: str | None = typer.Option(None, help="Expected answer (for logging)"),
    rounds: int | None = typer.Option(None, help="Max verify-teach rounds"),
    save: bool = typer.Option(True, help="Save the JSON trace under runs/"),
    formalizer: str | None = typer.Option(
        None, help="Formalizer provider: falcon (default) | openai | openrouter"
    ),
    verbose: bool = typer.Option(False, "-v"),
) -> None:
    """Solve one problem with Falcon under Lean 4 supervision."""
    logging.basicConfig(level=logging.INFO if verbose else logging.WARNING)
    settings = _settings(formalizer)
    console.print(
        f"[dim]student={settings.student.model}  formalizer={settings.formalizer.model}[/]"
    )
    agent = VerifyAndTeachAgent(settings, on_event=_print_event)
    trace = agent.run(problem, expected_answer=expected, max_rounds=rounds)
    console.rule("[bold]Result")
    console.print(
        f"status=[bold]{trace.status}[/] final_answer=[bold]{trace.final_answer}[/] "
        f"assurance={trace.assurance_score} rounds={trace.n_rounds} "
        f"time={trace.total_latency_s}s"
    )
    if save:
        p = agent.save_trace(trace)
        console.print(f"trace saved to {p}")


@app.command()
def check(prop: list[str] = typer.Argument(..., help="Lean 4 Prop(s) to decide")) -> None:
    """Directly ask the Lean kernel about one or more propositions."""
    from .lean_runner import LeanRunner

    settings = Settings.from_env()
    runner = LeanRunner(settings.lean_project_dir, settings.lean_timeout)
    res = runner.check_claims({f"c{i}": p for i, p in enumerate(prop)})
    for i, p in enumerate(prop):
        o = res.outcomes[f"c{i}"]
        console.print(f"[{VERDICT_STYLE[o.verdict]}]{o.verdict.value:10}[/] {p}  {o.detail}")


@app.command()
def bench(
    dataset: Path = typer.Option(Path("bench/problems.jsonl"), help="JSONL problems"),
    out: Path = typer.Option(Path("bench/results"), help="Output directory"),
    limit: int | None = typer.Option(None),
    rounds: int | None = typer.Option(None),
    mode: str = typer.Option("both", help="baseline | verified | both"),
    workers: int = typer.Option(4, help="Parallel problems"),
    tag: str | None = typer.Option(None, help="Filter by tag (math|logic)"),
    formalizer: str | None = typer.Option(
        None, help="Formalizer provider: falcon (default) | openai | openrouter"
    ),
) -> None:
    """Run baseline Falcon vs. Falcon+FalconVerifier on a dataset and report accuracy."""
    from .bench import run_benchmark

    run_benchmark(
        dataset,
        out,
        limit=limit,
        rounds=rounds,
        mode=mode,
        workers=workers,
        tag=tag,
        settings=_settings(formalizer),
    )


@app.command("bench-regrade")
def bench_regrade(
    run_dir: list[Path] = typer.Argument(..., help="bench/results/<arm>/run_* directories"),
) -> None:
    """Re-grade stored benchmark runs with the current answer matcher (no model calls)."""
    from .bench import print_summary, regrade_run

    for d in run_dir:
        print_summary(regrade_run(d)["summary"])


@app.command("export-dpo")
def export_dpo(
    roots: list[Path] = typer.Argument(
        None, help="Trace files or directories (default: bench/results and runs)"
    ),
    out: Path = typer.Option(Path("data/dpo_pairs.jsonl"), help="Output JSONL"),
    allow_unlabeled: bool = typer.Option(
        False, help="Also use traces without a gold answer (chosen = Lean-verified only)"
    ),
) -> None:
    """Export Lean-refuted -> Lean-verified answer pairs as DPO preference data."""
    from .dpo_export import export

    stats = export(
        roots or [Path("bench/results"), Path("runs")], out, require_expected=not allow_unlabeled
    )
    console.print(
        f"[green]{stats['pairs']} pairs[/] ({stats['ar']} ar / {stats['en']} en) from "
        f"{stats['traces']} traces, {stats['duplicates']} duplicates dropped -> {out}"
    )


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0"), port: int = typer.Option(8000), reload: bool = False
) -> None:
    """Start the web UI / API."""
    import uvicorn

    uvicorn.run("falconverifier.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
