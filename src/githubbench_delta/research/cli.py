"""Typer sub-app: githubbench research …"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from githubbench_delta.research.artifacts import ExperimentArtifactManager
from githubbench_delta.research.dashboard import ValidationDashboard
from githubbench_delta.research.power import MDEEstimator, SampleSizeEstimator
from githubbench_delta.research.publish import PublicationExporter
from githubbench_delta.research.registry import ExperimentRegistry
from githubbench_delta.research.repro import ReproducibilityPackage
from githubbench_delta.research.scheduler import ExperimentScheduler

research_app = typer.Typer(
    help="Research execution platform — manifests, stats readiness, validation dashboard.",
    no_args_is_help=True,
)
console = Console(width=120, soft_wrap=True)


def _registry(
    experiments_dir: Path | None = None,
    evidence_path: Path | None = None,
) -> ExperimentRegistry:
    reg = ExperimentRegistry(
        experiments_dir=experiments_dir,
        evidence_path=evidence_path,
    )
    reg.reload()
    return reg


@research_app.command("list")
def research_list(
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
    evidence_path: Path | None = typer.Option(None, "--evidence"),
) -> None:
    """List registered research experiments (YAML auto-discovery)."""

    reg = _registry(experiments_dir, evidence_path)
    table = Table(title="Research experiments")
    table.add_column("ID")
    table.add_column("Project")
    table.add_column("Status")
    table.add_column("Title")
    for exp in reg.list_experiments():
        table.add_row(exp.id, exp.project, exp.status, exp.title)
    console.print(table)
    console.print(f"[dim]{len(reg.list_experiments())} experiments from registry[/dim]")


@research_app.command("status")
def research_status(
    experiment: str | None = typer.Option(None, "--experiment", "-e"),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
    evidence_path: Path | None = typer.Option(None, "--evidence"),
) -> None:
    """Show readiness status for one or all experiments."""

    reg = _registry(experiments_dir, evidence_path)
    sched = ExperimentScheduler(reg)
    statuses = [sched.status(experiment)] if experiment else sched.all_statuses()
    statuses = [s for s in statuses if s is not None]
    if not statuses:
        console.print("[red]No experiments found[/red]")
        raise typer.Exit(1)
    table = Table(title="Research readiness")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Missing nodes")
    table.add_column("Pub ready")
    table.add_column("Notes")
    for s in statuses:
        table.add_row(
            s.experiment_id,
            s.status,
            ", ".join(s.missing_evidence_nodes) or "—",
            "yes" if s.publication_ready else "no",
            "; ".join(s.notes)[:80],
        )
    console.print(table)


@research_app.command("artifacts")
def research_artifacts(
    experiment: str = typer.Option(..., "--experiment", "-e"),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
    seed: int | None = typer.Option(None, "--seed"),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
) -> None:
    """Write experiment_manifest.json, metadata, and summary for an experiment."""

    reg = _registry(experiments_dir)
    exp = reg.get(experiment)
    if exp is None:
        console.print(f"[red]Unknown experiment:[/red] {experiment}")
        raise typer.Exit(1)
    mgr = ExperimentArtifactManager()
    dest = mgr.write(exp, out_dir=output_dir, seed=seed)
    ReproducibilityPackage().write(exp, dest, seed=seed)
    console.print(f"[green]Wrote artifacts[/green] → {dest}")


@research_app.command("publish")
def research_publish(
    experiment: str = typer.Option(..., "--experiment", "-e"),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
) -> None:
    """Export publication tables/figures from real evaluation aggregates only."""

    reg = _registry(experiments_dir)
    exp = reg.get(experiment)
    if exp is None:
        console.print(f"[red]Unknown experiment:[/red] {experiment}")
        raise typer.Exit(1)
    mgr = ExperimentArtifactManager()
    dest = Path(output_dir) if output_dir else mgr.output_dir(exp.id)
    dest.mkdir(parents=True, exist_ok=True)
    paths = PublicationExporter().export(exp, dest)
    n = paths.get("n_rows", 0)
    console.print(f"[green]Publish export[/green] → {dest} ({n} real rows)")
    if n == 0:
        console.print(
            "[yellow]No aggregate rows matched — empty tables written "
            "(no fabricated numbers)[/yellow]"
        )


@research_app.command("repro")
def research_repro(
    experiment: str = typer.Option(..., "--experiment", "-e"),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
    seed: int | None = typer.Option(None, "--seed"),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
) -> None:
    """Write reproducibility package (environment, deps, config, seeds)."""

    reg = _registry(experiments_dir)
    exp = reg.get(experiment)
    if exp is None:
        console.print(f"[red]Unknown experiment:[/red] {experiment}")
        raise typer.Exit(1)
    mgr = ExperimentArtifactManager()
    dest = Path(output_dir) if output_dir else mgr.output_dir(exp.id)
    dest.mkdir(parents=True, exist_ok=True)
    repro = ReproducibilityPackage().write(exp, dest, seed=seed)
    console.print(f"[green]Repro package[/green] → {repro}")


@research_app.command("validate")
def research_validate(
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
    evidence_path: Path | None = typer.Option(None, "--evidence"),
) -> None:
    """Build validation_report.html from registry + evidence + readiness."""

    reg = _registry(experiments_dir, evidence_path)
    dash = ValidationDashboard(reg)
    out = Path(output_dir) if output_dir else Path("results/research/validation_report.html")
    if out.is_dir() or str(out).endswith("/"):
        out = Path(out) / "validation_report.html"
    path = dash.write(out)
    console.print(f"[green]Validation report[/green] → {path}")


@research_app.command("power")
def research_power(
    pilot_json: Path = typer.Option(..., "--pilot-json", help="JSON file with numeric array"),
    alpha: float = typer.Option(0.05, "--alpha"),
    power: float = typer.Option(0.8, "--power"),
    mde: float | None = typer.Option(None, "--mde"),
    n: int | None = typer.Option(None, "--n", help="Fixed n for MDE estimate"),
) -> None:
    """Estimate sample size or MDE from a real pilot array (never invents pilots)."""

    try:
        raw = json.loads(pilot_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[red]Could not read pilot JSON:[/red] {exc}")
        raise typer.Exit(1) from exc
    if isinstance(raw, dict) and "values" in raw:
        values = raw["values"]
    elif isinstance(raw, list):
        values = raw
    else:
        console.print('[red]Pilot JSON must be a list or {"values": [...]}[/red]')
        raise typer.Exit(1)

    if mde is not None:
        est = SampleSizeEstimator().estimate(values, alpha=alpha, power=power, mde=mde)
    else:
        est = MDEEstimator().estimate(values, n=n, alpha=alpha, power=power)

    if not est.ok:
        console.print(f"[yellow]insufficient_data[/yellow]: {'; '.join(est.notes)}")
        raise typer.Exit(2)

    console.print(est.model_dump_json(indent=2))
