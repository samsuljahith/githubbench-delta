"""Typer sub-app: githubbench memorization …"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from githubbench_delta.memorization.engine import MemorizationEngine
from githubbench_delta.memorization.report import (
    MemorizationReportGenerator,
    default_report_dir,
)
from githubbench_delta.memorization.twins import TwinTaskGenerator
from githubbench_delta.memorization.validate import TwinValidator

memorization_app = typer.Typer(
    help="Memorization Discounted Scoring — post-process memorization vs capability.",
    no_args_is_help=True,
)
console = Console(width=120, soft_wrap=True)


def _print_summary(report) -> None:
    console.print(
        f"[green]MDS[/green] mode={report.mode} agents={len(report.breakdowns)} "
        f"experiments={report.experiment_ids}"
    )
    if not report.breakdowns:
        return
    table = Table(title="Capability breakdown")
    table.add_column("Agent")
    table.add_column("S_obs", justify="right")
    table.add_column("G", justify="right")
    table.add_column("L", justify="right")
    table.add_column("S_disc", justify="right")
    for b in report.breakdowns:
        table.add_row(
            b.agent_id,
            f"{b.observed_score:.3f}",
            f"{b.generalization:.3f}",
            f"{b.memorization_lift:.3f}",
            f"{b.discounted_score:.3f}",
        )
    console.print(table)


@memorization_app.command("analyze")
def memorization_analyze(
    experiment: list[str] = typer.Option(
        ...,
        "--experiment",
        "-e",
        help="Experiment id (repeatable)",
    ),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
    twins_path: Path | None = typer.Option(
        None,
        "--twins-path",
        help="Optional twin tasks JSONL sidecar",
    ),
) -> None:
    """Estimate memorization lift and write JSON + Markdown + HTML dashboard."""

    engine = MemorizationEngine(results_dir=experiments_dir)
    generator = MemorizationReportGenerator(engine=engine)
    out = Path(output_dir) if output_dir else default_report_dir()
    report = generator.generate(
        list(experiment),
        out,
        formats={"json", "markdown", "html"},
        twins_path=twins_path,
    )
    _print_summary(report)
    console.print(f"[cyan]Wrote[/cyan] {report.output_dir} → {', '.join(report.artifacts)}")


@memorization_app.command("report")
def memorization_report(
    experiment: list[str] = typer.Option(..., "--experiment", "-e"),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
    twins_path: Path | None = typer.Option(None, "--twins-path"),
) -> None:
    """Generate the full MDS report bundle (alias of analyze)."""

    memorization_analyze(
        experiment=experiment,
        output_dir=output_dir,
        experiments_dir=experiments_dir,
        twins_path=twins_path,
    )


@memorization_app.command("export")
def memorization_export(
    experiment: list[str] = typer.Option(..., "--experiment", "-e"),
    output_dir: Path | None = typer.Option(None, "--output", "-o"),
    experiments_dir: Path | None = typer.Option(None, "--experiments-dir"),
    twins_path: Path | None = typer.Option(None, "--twins-path"),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Export format: json | markdown | html (or comma-separated)",
    ),
) -> None:
    """Export selected MDS formats."""

    parts = {p.strip().lower() for p in fmt.split(",") if p.strip()}
    allowed = {"json", "markdown", "html"}
    unknown = parts - allowed
    if unknown:
        console.print(f"[red]Unknown format(s): {', '.join(sorted(unknown))}[/red]")
        raise typer.Exit(code=2)
    engine = MemorizationEngine(results_dir=experiments_dir)
    generator = MemorizationReportGenerator(engine=engine)
    out = Path(output_dir) if output_dir else default_report_dir()
    report = generator.generate(list(experiment), out, formats=parts, twins_path=twins_path)
    _print_summary(report)
    console.print(f"[cyan]Exported[/cyan] formats={sorted(parts)} → {report.output_dir}")


@memorization_app.command("generate-twins")
def memorization_generate_twins(
    dataset: Path = typer.Option(
        ...,
        "--dataset",
        help="Dataset directory (with tasks.jsonl) or tasks.jsonl path",
    ),
    output: Path = typer.Option(
        Path("results/memorization/twins/twins.jsonl"),
        "--output",
        "-o",
        help="Sidecar twin JSONL output path",
    ),
) -> None:
    """Emit paraphrase twin task specs (does not run agents or mutate corpus)."""

    gen = TwinTaskGenerator()
    specs = gen.generate_from_dataset(dataset)
    from githubbench_delta.memorization.twins import _load_raw_jsonl

    src = dataset if dataset.suffix == ".jsonl" else dataset / "tasks.jsonl"
    parent_rows = {str(r["id"]): r for r in _load_raw_jsonl(src)}
    TwinValidator().validate_catalog(specs, parents=parent_rows)
    path = gen.write_jsonl(specs, output)
    console.print(f"[green]Generated[/green] {len(specs)} twins → {path}")
