"""Typer CLI entrypoint for GitHubBench-Delta."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from githubbench_delta import __version__
from githubbench_delta.agents.registry import list_agent_ids
from githubbench_delta.benchmark.runner import BenchmarkRunner
from githubbench_delta.core.config import clear_config_cache, load_config
from githubbench_delta.core.errors import GitHubBenchError
from githubbench_delta.datasets.manifest import generate_manifest, write_manifest
from githubbench_delta.datasets.validators import DatasetValidator
from githubbench_delta.metrics.registry import catalog_entries, list_metric_ids
from githubbench_delta.observability.logging import configure_cli_logging
from githubbench_delta.observatory.cli import observatory_app
from githubbench_delta.pipeline.experiment import ExperimentRunner
from githubbench_delta.pipeline.experiment_manager import ExperimentManager
from githubbench_delta.pipeline.models import ExperimentSpec
from githubbench_delta.tasks.registry import list_task_categories

app = typer.Typer(
    name="githubbench",
    help="GitHubBench-Delta — evaluate AI coding agents on GitHub engineering tasks.",
    no_args_is_help=True,
)
list_app = typer.Typer(help="List registered agents, tasks, or metrics.")
app.add_typer(list_app, name="list")
config_app = typer.Typer(help="Inspect configuration.")
app.add_typer(config_app, name="config")
dataset_app = typer.Typer(help="Validate datasets and generate manifests.")
app.add_typer(dataset_app, name="dataset")
experiment_app = typer.Typer(help="Create and run evaluation experiments.")
app.add_typer(experiment_app, name="experiment")
report_app = typer.Typer(help="Generate publication reports from experiment artifacts.")
app.add_typer(report_app, name="report")
app.add_typer(observatory_app, name="observatory")

console = Console(width=120, soft_wrap=True)
logger = logging.getLogger("githubbench_delta.cli")


def _resolve_config_dir(config_dir: Path | None) -> Path | None:
    return config_dir


def _fail(exc: BaseException) -> None:
    console.print(f"[red]Error:[/red] {exc}")
    logger.debug("CLI failure", exc_info=exc)
    raise typer.Exit(code=1) from exc


@app.callback()
def main(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable DEBUG logging",
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Log level: critical|error|warning|info|debug",
    ),
    structured_logs: bool = typer.Option(
        True,
        "--structured-logs/--plain-logs",
        help="Emit JSON structured logs (default) or plain text",
    ),
) -> None:
    """GitHubBench-Delta CLI."""

    level = "debug" if verbose else log_level
    configure_cli_logging(level=level, structured=structured_logs)


@app.command("version")
def version_cmd() -> None:
    """Print the installed package version."""

    console.print(f"githubbench-delta {__version__}")


@config_app.command("show")
def config_show(
    config_dir: Path | None = typer.Option(
        None,
        "--config-dir",
        help="Directory containing default.yaml, agents.yaml, metrics.yaml",
    ),
) -> None:
    """Load and display the aggregated application configuration."""

    try:
        clear_config_cache()
        cfg = load_config(_resolve_config_dir(config_dir))
    except GitHubBenchError as exc:
        _fail(exc)
    console.print(f"[bold]seed[/bold]: {cfg.runtime.seed}")
    console.print(f"[bold]trial_count[/bold]: {cfg.runtime.trial_count}")
    console.print(f"[bold]agents[/bold]: {', '.join(sorted(cfg.agents))}")
    console.print(f"[bold]evaluators[/bold]: {len(cfg.evaluators)}")
    console.print(f"[bold]sqlite[/bold]: {cfg.runtime.storage.sqlite_path}")
    console.print(f"[bold]duckdb[/bold]: {cfg.runtime.storage.duckdb_path}")
    console.print(
        f"[bold]structured_logging[/bold]: {cfg.runtime.observability.structured_logging}"
    )


@list_app.command("agents")
def list_agents() -> None:
    """List registered agent ids."""

    table = Table(title="Agents")
    table.add_column("id")
    for agent_id in list_agent_ids():
        table.add_row(str(agent_id))
    console.print(table)


@list_app.command("tasks")
def list_tasks() -> None:
    """List registered task categories."""

    table = Table(title="Task categories")
    table.add_column("category")
    for category in list_task_categories():
        table.add_row(str(category))
    console.print(table)


@list_app.command("metrics")
def list_metrics(
    config_dir: Path | None = typer.Option(
        None,
        "--config-dir",
        help="Directory containing metrics.yaml",
    ),
) -> None:
    """List the 18 methodology evaluators."""

    clear_config_cache()
    cfg = load_config(_resolve_config_dir(config_dir))
    table = Table(title="Metrics catalog")
    table.add_column("id")
    table.add_column("display_name")
    table.add_column("group")
    table.add_column("weight")
    table.add_column("enabled")
    for row in catalog_entries(cfg):
        table.add_row(
            str(row["id"]),
            str(row["display_name"]),
            str(row["group"]),
            str(row["weight"]),
            str(row["enabled"]),
        )
    console.print(table)
    console.print("ids: " + ",".join(list_metric_ids()))
    console.print(f"Total: {len(list_metric_ids())} evaluators")


@dataset_app.command("validate")
def dataset_validate(
    path: Path = typer.Argument(..., help="Dataset directory or task file"),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Run Phase 3.5 CorpusQualityValidator checks (counts, tools, fixtures).",
    ),
) -> None:
    """Validate a dataset directory or task file against schemas."""

    try:
        runner = BenchmarkRunner(base_path=Path.cwd(), validate=False)
        if path.is_dir():
            catalog = runner.load_dataset(path)
            DatasetValidator(
                base_path=Path.cwd(),
                strict_corpus=strict,
            ).validate_tasks(
                catalog.all(),
                metadata=runner.metadata,
                manifest_path=(path / "manifest.json") if strict else None,
            )
        else:
            catalog = runner.load_file(path)
            DatasetValidator(
                base_path=Path.cwd(),
                strict_corpus=strict,
            ).validate_tasks(catalog.all())
    except GitHubBenchError as exc:
        _fail(exc)
    label = "strict OK" if strict else "OK"
    console.print(f"[green]{label}[/green] {len(catalog)} task(s) validated from {path}")


@dataset_app.command("manifest")
def dataset_manifest(
    path: Path = typer.Argument(..., help="Dataset directory"),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Output path (default: <dataset>/manifest.json)",
    ),
) -> None:
    """Generate manifest.json for a dataset directory."""

    if not path.is_dir():
        raise typer.BadParameter("manifest requires a dataset directory")
    try:
        runner = BenchmarkRunner(base_path=Path.cwd(), validate=True)
        catalog = runner.load_dataset(path)
        manifest = generate_manifest(catalog.all(), metadata=runner.metadata)
        out = output or (path / "manifest.json")
        write_manifest(manifest, out)
    except GitHubBenchError as exc:
        _fail(exc)
    console.print(f"Wrote {out} ({manifest.task_count} tasks, hash={manifest.content_hash[:16]}…)")


@experiment_app.command("create")
def experiment_create(
    dataset: Path = typer.Option(..., "--dataset", help="Dataset directory"),
    agent: list[str] = typer.Option([], "--agent", help="Agent id (repeatable)"),
    task: list[str] = typer.Option([], "--task", help="Task id (repeatable)"),
    trials: int = typer.Option(1, "--trials", help="Trials per task/agent"),
    seed: int = typer.Option(42, "--seed", help="RNG seed for sampling and trials"),
    name: str = typer.Option("", "--name", help="Optional human-readable experiment name"),
    config_dir: Path | None = typer.Option(None, "--config-dir", help="Override configs directory"),
) -> None:
    """Create an experiment manifest without executing agents."""

    try:
        clear_config_cache()
        cfg = load_config(_resolve_config_dir(config_dir))
        mgr = ExperimentManager(app_config=cfg)
        bench = BenchmarkRunner(base_path=Path.cwd(), validate=True)
        bench.load_dataset(dataset)
        task_ids = list(task) if task else [t.id for t in bench.full(seed=seed)]
        agent_ids = list(agent) if agent else list_agent_ids()
        spec = ExperimentSpec(
            dataset_path=dataset,
            agent_ids=[str(a) for a in agent_ids],
            task_ids=task_ids,
            trial_count=trials,
            seed=seed,
            name=name,
        )
        manifest = mgr.create(spec, task_ids=task_ids)
    except GitHubBenchError as exc:
        _fail(exc)
    console.print(
        f"[green]Created[/green] {manifest.experiment_id} "
        f"({len(task_ids)} tasks, {len(agent_ids)} agents, {trials} trials)"
    )


@experiment_app.command("run")
def experiment_run(
    dataset: Path = typer.Option(..., "--dataset", help="Dataset directory"),
    agent: list[str] = typer.Option([], "--agent", help="Agent id (repeatable)"),
    task: list[str] = typer.Option([], "--task", help="Task id (repeatable)"),
    trials: int = typer.Option(1, "--trials", help="Trials per task/agent"),
    seed: int = typer.Option(42, "--seed", help="RNG seed for sampling and trials"),
    concurrency: int = typer.Option(1, "--concurrency", help="Max concurrent evaluation units"),
    resume: bool = typer.Option(
        True, "--resume/--no-resume", help="Resume incomplete runs when possible"
    ),
    cache: bool = typer.Option(
        True, "--cache/--no-cache", help="Reuse cached evaluation results when present"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Skip live agents; synthesize AgentResults from gold answers",
    ),
    name: str = typer.Option("", "--name", help="Optional human-readable experiment name"),
    config_dir: Path | None = typer.Option(None, "--config-dir", help="Override configs directory"),
    record_observatory: bool = typer.Option(
        False,
        "--record-observatory/--no-record-observatory",
        help="After a successful run, append a Half-Life Observatory snapshot (default: off)",
    ),
) -> None:
    """Run an end-to-end evaluation experiment."""

    try:
        clear_config_cache()
        cfg = load_config(_resolve_config_dir(config_dir))
        agent_ids = [str(a) for a in agent] if agent else [str(a) for a in list_agent_ids()]
        spec = ExperimentSpec(
            dataset_path=dataset,
            agent_ids=agent_ids,
            task_ids=list(task) if task else None,
            trial_count=trials,
            seed=seed,
            max_concurrency=concurrency,
            resume=resume,
            use_cache=cache,
            dry_run=dry_run,
            name=name,
        )
        runner = ExperimentRunner(app_config=cfg)
        manifest = asyncio.run(runner.run(spec))
    except GitHubBenchError as exc:
        _fail(exc)
    console.print(
        f"[green]{manifest.status}[/green] experiment={manifest.experiment_id} "
        f"tasks={len(manifest.task_ids)} agents={manifest.agent_ids}"
    )
    if record_observatory and str(manifest.status).lower() == "completed":
        from githubbench_delta.observatory.ingest import ingest_experiments

        written, skipped = ingest_experiments(experiment_ids=[manifest.experiment_id])
        console.print(
            f"[cyan]observatory[/cyan] recorded snapshots written={written} skipped={skipped}"
        )


@experiment_app.command("status")
def experiment_status(
    experiment_id: str = typer.Argument(..., help="Experiment id"),
    config_dir: Path | None = typer.Option(None, "--config-dir", help="Override configs directory"),
) -> None:
    """Show experiment.json / run.json status."""

    try:
        clear_config_cache()
        cfg = load_config(_resolve_config_dir(config_dir))
        mgr = ExperimentManager(app_config=cfg)
        manifest = mgr.load(experiment_id)
    except GitHubBenchError as exc:
        _fail(exc)
    run_path = mgr.experiment_dir(experiment_id) / "run.json"
    console.print(f"experiment_id={manifest.experiment_id}")
    console.print(f"status={manifest.status}")
    console.print(f"tasks={len(manifest.task_ids)} agents={manifest.agent_ids}")
    if run_path.is_file():
        import json

        run: dict[str, Any] = json.loads(run_path.read_text(encoding="utf-8"))
        console.print(
            f"run={run.get('run_id')} units_done={run.get('units_done')}/"
            f"{run.get('units_total')} failed={run.get('units_failed')}"
        )


@report_app.command("generate")
def report_generate(
    experiment: list[str] = typer.Option(
        ...,
        "--experiment",
        "-e",
        help="Experiment id (repeatable)",
    ),
    report_type: str = typer.Option(
        "technical",
        "--type",
        "-t",
        help="executive|technical|experiment|agent_comparison|metric|task_analysis|regression|ci_summary",
    ),
    formats: list[str] = typer.Option(
        ["markdown"],
        "--format",
        "-f",
        help="markdown|html|pdf|json|csv (repeatable)",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output directory"),
    template_dir: Path | None = typer.Option(
        None, "--template-dir", help="Custom Jinja2 template directory"
    ),
    config_dir: Path | None = typer.Option(None, "--config-dir", help="Override configs directory"),
) -> None:
    """Generate a report from completed experiment artifacts."""

    from githubbench_delta.reports.builder import ReportBuilder
    from githubbench_delta.reports.cli_helpers import build_request

    try:
        clear_config_cache()
        load_config(_resolve_config_dir(config_dir))
        request = build_request(
            experiment=experiment,
            report_type=report_type,
            formats=formats,
            output=output,
            template_dir=template_dir,
        )
        paths = ReportBuilder().generate(request)
    except (GitHubBenchError, ValueError) as exc:
        _fail(exc)
    if not paths:
        console.print("[red]No report files written[/red]")
        raise typer.Exit(code=1)
    for path in paths:
        console.print(f"[green]Wrote[/green] {path}")


@report_app.command("compare")
def report_compare(
    baseline: str = typer.Option(..., "--baseline", "-b", help="Baseline experiment id"),
    candidate: str = typer.Option(..., "--candidate", "-c", help="Candidate experiment id"),
    report_type: str = typer.Option(
        "regression",
        "--type",
        "-t",
        help="Report type (default: regression)",
    ),
    formats: list[str] = typer.Option(
        ["markdown"],
        "--format",
        "-f",
        help="markdown|html|pdf|json|csv (repeatable)",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output directory"),
    template_dir: Path | None = typer.Option(
        None, "--template-dir", help="Custom Jinja2 template directory"
    ),
    config_dir: Path | None = typer.Option(None, "--config-dir", help="Override configs directory"),
) -> None:
    """Compare two experiments and emit a regression/diff report."""

    from githubbench_delta.reports.builder import ReportBuilder
    from githubbench_delta.reports.cli_helpers import build_request

    try:
        clear_config_cache()
        load_config(_resolve_config_dir(config_dir))
        request = build_request(
            experiment=[baseline, candidate],
            report_type=report_type,
            formats=formats,
            output=output,
            template_dir=template_dir,
            baseline=baseline,
            candidate=candidate,
        )
        paths = ReportBuilder().generate(request)
    except (GitHubBenchError, ValueError) as exc:
        _fail(exc)
    if not paths:
        console.print("[red]No report files written[/red]")
        raise typer.Exit(code=1)
    for path in paths:
        console.print(f"[green]Wrote[/green] {path}")


@report_app.command("export")
def report_export(
    experiment: str = typer.Option(..., "--experiment", "-e", help="Experiment id"),
    format: str = typer.Option(
        "csv",
        "--format",
        "-f",
        help="csv|json|markdown|html|pdf",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output directory or file path"
    ),
    config_dir: Path | None = typer.Option(None, "--config-dir", help="Override configs directory"),
) -> None:
    """Export structured evaluation data for an experiment."""

    from githubbench_delta.reports.builder import ReportBuilder
    from githubbench_delta.reports.cli_helpers import build_request

    try:
        clear_config_cache()
        load_config(_resolve_config_dir(config_dir))
        out_dir = output.parent if output is not None and output.suffix else output
        request = build_request(
            experiment=[experiment],
            report_type="technical",
            formats=[format],
            output=out_dir,
        )
        builder = ReportBuilder()
        doc = builder.build(request)
        preferred = output.stem if output is not None and output.suffix else None
        paths = builder.export(doc, request, preferred_name=preferred)
        if output is not None and output.suffix and paths:
            target = output
            target.parent.mkdir(parents=True, exist_ok=True)
            if paths[0] != target:
                paths[0].replace(target)
                paths = [target]
    except (GitHubBenchError, ValueError) as exc:
        _fail(exc)
    if not paths:
        console.print("[red]No export written[/red]")
        raise typer.Exit(code=1)
    for path in paths:
        console.print(f"[green]Wrote[/green] {path}")


if __name__ == "__main__":
    app()
