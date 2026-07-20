"""Typer sub-app: githubbench observatory …"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from githubbench_delta.observatory.export import ObservatoryExporter, default_report_dir
from githubbench_delta.observatory.half_life import HalfLifeEstimator
from githubbench_delta.observatory.history import DEFAULT_HISTORY_DIR, BenchmarkHistory
from githubbench_delta.observatory.ingest import ingest_experiments
from githubbench_delta.observatory.trends import TrendAnalyzer

observatory_app = typer.Typer(
    help="Half-Life Observatory — longitudinal benchmark aging analysis.",
    no_args_is_help=True,
)
console = Console(width=120, soft_wrap=True)


def _history_dir(path: Path | None) -> Path:
    return Path(path) if path else DEFAULT_HISTORY_DIR


@observatory_app.command("ingest")
def observatory_ingest(
    experiments_dir: Path | None = typer.Option(
        None,
        "--experiments-dir",
        help="Directory containing experiment_* folders (default: config results_dir)",
    ),
    experiment: list[str] = typer.Option(
        [],
        "--experiment",
        "-e",
        help="Experiment id to ingest (repeatable; default: all)",
    ),
    history_dir: Path | None = typer.Option(
        None,
        "--history-dir",
        help=f"Observatory history directory (default: {DEFAULT_HISTORY_DIR})",
    ),
) -> None:
    """Append snapshots from completed experiments into observatory history."""

    written, skipped = ingest_experiments(
        experiment_ids=list(experiment) or None,
        results_dir=experiments_dir,
        history_dir=_history_dir(history_dir),
    )
    summary = BenchmarkHistory(history_dir=_history_dir(history_dir)).summary()
    console.print(
        f"[green]Ingested[/green] written={written} skipped={skipped} "
        f"history_count={summary.get('count', 0)}"
    )


@observatory_app.command("analyze")
def observatory_analyze(
    history_dir: Path | None = typer.Option(None, "--history-dir"),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Fit decay / half-life and write JSON + Markdown + charts."""

    out = Path(output_dir) if output_dir else default_report_dir()
    exporter = ObservatoryExporter(history_dir=_history_dir(history_dir))
    path = exporter.export(out, formats={"json", "markdown", "html"})
    estimate, _trends, events = exporter.analyze()
    console.print(f"[green]Analyzed[/green] → {path}")
    console.print(
        f"half_life={HalfLifeEstimator.format_half_life(estimate.half_life_days)} "
        f"confidence={estimate.confidence:.3f} trend={estimate.usefulness_trend} "
        f"regressions={len(events)}"
    )


@observatory_app.command("trend")
def observatory_trend(
    history_dir: Path | None = typer.Option(None, "--history-dir"),
    provider: bool = typer.Option(False, "--provider", help="Show provider trends"),
    model: bool = typer.Option(False, "--model", help="Show model progression"),
) -> None:
    """Print score / provider / model trend tables from history."""

    history = BenchmarkHistory(history_dir=_history_dir(history_dir))
    snaps = history.load()
    if not snaps:
        console.print("[yellow]No snapshots in history. Run `observatory ingest` first.[/yellow]")
        raise typer.Exit(code=1)
    trends = TrendAnalyzer().analyze(snaps)

    if provider:
        table = Table(title="Provider trends")
        table.add_column("Provider")
        table.add_column("Timestamp")
        table.add_column("Score", justify="right")
        table.add_column("Agent")
        for prov, pts in sorted(trends.provider_trends.items()):
            for p in pts:
                table.add_row(prov, p.timestamp.isoformat(), f"{p.value:.4f}", p.label)
        console.print(table)
        return

    if model:
        table = Table(title="Model progression")
        table.add_column("Model")
        table.add_column("Timestamp")
        table.add_column("Score", justify="right")
        for mk, pts in sorted(trends.model_progression.items()):
            for p in pts:
                table.add_row(mk, p.timestamp.isoformat(), f"{p.value:.4f}")
        console.print(table)
        return

    table = Table(title="Score vs time")
    table.add_column("Timestamp")
    table.add_column("Agent")
    table.add_column("Score", justify="right")
    table.add_column("Provider")
    table.add_column("Model")
    for p in trends.score_vs_time:
        table.add_row(
            p.timestamp.isoformat(),
            p.label,
            f"{p.value:.4f}",
            str(p.metadata.get("provider", "")),
            str(p.metadata.get("model", "")),
        )
    console.print(table)

    sat = Table(title="Cohort saturation / differentiation")
    sat.add_column("Timestamp")
    sat.add_column("S(t)", justify="right")
    sat.add_column("D(t)", justify="right")
    for s, d in zip(trends.saturation_vs_time, trends.differentiation_vs_time, strict=True):
        sat.add_row(s.timestamp.isoformat(), f"{s.value:.4f}", f"{d.value:.4f}")
    console.print(sat)


@observatory_app.command("report")
def observatory_report(
    history_dir: Path | None = typer.Option(None, "--history-dir"),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    """Generate the full half-life narrative report (alias of analyze)."""

    observatory_analyze(history_dir=history_dir, output_dir=output_dir)


@observatory_app.command("export")
def observatory_export(
    history_dir: Path | None = typer.Option(None, "--history-dir"),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Export format: json | markdown | html (or comma-separated)",
    ),
) -> None:
    """Export selected formats from history."""

    parts = {p.strip().lower() for p in fmt.split(",") if p.strip()}
    allowed = {"json", "markdown", "html"}
    unknown = parts - allowed
    if unknown:
        console.print(f"[red]Unknown format(s): {', '.join(sorted(unknown))}[/red]")
        raise typer.Exit(code=2)
    out = Path(output_dir) if output_dir else default_report_dir()
    exporter = ObservatoryExporter(history_dir=_history_dir(history_dir))
    path = exporter.export(out, formats=parts)
    console.print(f"[green]Exported[/green] formats={sorted(parts)} → {path}")
