"""Load report source data from ExperimentRepository (and RunSummary adapter)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from githubbench_delta import __version__
from githubbench_delta.core.config import METHODOLOGY_METRIC_IDS, load_config
from githubbench_delta.core.models import RunSummary
from githubbench_delta.dashboard.aggregations import (
    build_leaderboard,
    build_metric_stats,
    build_overview,
    build_task_rows,
)
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.metrics.registry import get_metric_group
from githubbench_delta.reports.models import BrandConfig, ReportDocument, ReportRequest, ReportType


def make_repository(request: ReportRequest) -> ExperimentRepository:
    cfg = load_config()
    return ExperimentRepository(
        results_dir=request.results_dir or cfg.runtime.pipeline.results_dir,
        sqlite_path=request.sqlite_path or cfg.runtime.storage.sqlite_path,
        app_config=cfg,
    )


def _meta_version(experiment: dict[str, Any], key: str) -> str | None:
    meta = experiment.get("metadata") or {}
    if isinstance(meta, dict) and meta.get(key):
        return str(meta[key])
    snap = experiment.get("config_snapshot") or {}
    if isinstance(snap, dict):
        if snap.get(key):
            return str(snap[key])
        nested = snap.get("dataset") or snap.get("prompts") or {}
        if isinstance(nested, dict) and nested.get(key):
            return str(nested[key])
        if key == "dataset_version" and nested.get("version"):
            return str(nested["version"])
        if key == "prompt_version" and nested.get("version"):
            return str(nested["version"])
    return None


def _category_means(rows: list[Any]) -> dict[str, float]:
    acc: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        cat = r.category or "unknown"
        if r.overall_score is not None:
            acc[cat].append(float(r.overall_score))
    return {k: sum(v) / len(v) for k, v in acc.items() if v}


def _title_for(report_type: ReportType, experiment_ids: list[str]) -> str:
    labels = {
        ReportType.EXECUTIVE: "Executive Summary",
        ReportType.TECHNICAL: "Technical Report",
        ReportType.EXPERIMENT: "Experiment Report",
        ReportType.AGENT_COMPARISON: "Agent Comparison Report",
        ReportType.METRIC: "Metric Report",
        ReportType.TASK_ANALYSIS: "Task Analysis Report",
        ReportType.REGRESSION: "Regression Report",
        ReportType.CI_SUMMARY: "CI Summary Report",
    }
    base = labels[report_type]
    if experiment_ids:
        return f"{base}: {', '.join(experiment_ids)}"
    return base


def load_report_document(
    repo: ExperimentRepository,
    request: ReportRequest,
) -> ReportDocument:
    """Assemble a ReportDocument skeleton with aggregated source tables."""

    exp_ids = list(request.experiment_ids)
    if request.baseline_id and request.candidate_id:
        for eid in (request.baseline_id, request.candidate_id):
            if eid not in exp_ids:
                exp_ids.append(eid)
    if not exp_ids:
        exp_ids = repo.list_experiment_ids()[:1]

    primary = exp_ids[0] if exp_ids else ""
    detail = repo.get_experiment(primary) if primary else None
    experiment = detail.experiment if detail else {}
    run = detail.run if detail else None

    rows = repo.all_evaluation_rows(exp_ids if exp_ids else None)
    if request.agent_id:
        rows = [r for r in rows if r.agent_id == request.agent_id]

    board, _ = build_leaderboard(
        repo,
        experiment_ids=exp_ids or None,
        agent_id=request.agent_id,
        page=1,
        page_size=100,
    )
    tasks, _ = build_task_rows(repo, experiment_ids=exp_ids or None, page=1, page_size=500)
    metric_stats = build_metric_stats(repo, experiment_ids=exp_ids or None)
    overview = build_overview(repo)

    methodology = []
    for mid in METHODOLOGY_METRIC_IDS:
        try:
            group = get_metric_group(mid).value
        except Exception:
            group = "unknown"
        methodology.append({"metric_id": mid, "group": group})

    appendix = {
        "package_version": __version__,
        "methodology_metrics": methodology,
        "artifact_paths": detail.artifacts if detail else [],
        "results_dir": str(repo.results_dir),
        "dataset_version": _meta_version(experiment, "dataset_version"),
        "prompt_version": _meta_version(experiment, "prompt_version"),
    }

    return ReportDocument(
        report_type=request.report_type,
        title=_title_for(request.report_type, exp_ids),
        experiment_ids=exp_ids,
        generated_at=datetime.now(UTC).isoformat(),
        brand=request.brand or BrandConfig(),
        leaderboard=[b.model_dump() for b in board],
        evaluations=[r.model_dump() for r in rows],
        tasks=[t.model_dump() for t in tasks],
        metric_stats=[m.model_dump() for m in metric_stats],
        category_scores=_category_means(rows),
        overview=overview.model_dump() if hasattr(overview, "model_dump") else dict(overview),
        experiment_detail={
            "experiment": experiment,
            "run": run,
            "summary": detail.summary if detail else {},
        },
        appendix=appendix,
        metadata={
            "agent_filter": request.agent_id,
            "dataset_version_filter": request.dataset_version,
            "prompt_version_filter": request.prompt_version,
            "dataset_path": experiment.get("dataset_path"),
            "seed": experiment.get("seed"),
            "trial_count": experiment.get("trial_count"),
            "agent_ids": experiment.get("agent_ids") or [],
            "task_ids": experiment.get("task_ids") or [],
        },
    )


def document_from_run_summary(
    summary: RunSummary,
    request: ReportRequest,
) -> ReportDocument:
    """Build a minimal ReportDocument when only a RunSummary is available."""

    evaluations: list[dict[str, Any]] = []
    for ev in summary.evaluations:
        evaluations.append(
            {
                "experiment_id": str(summary.metadata.get("experiment_id") or summary.run_id),
                "run_id": summary.run_id,
                "unit_key": f"{ev.trial.task_id}::{ev.trial.agent_id}::{ev.trial.trial_index}",
                "task_id": ev.trial.task_id,
                "agent_id": str(ev.trial.agent_id),
                "trial_index": ev.trial.trial_index,
                "overall_score": ev.overall_score,
                "confidence_score": ev.confidence_score,
                "group_scores": dict(ev.group_scores),
                "success": True,
                "category": (ev.metadata or {}).get("category"),
                "metric_scores": {
                    mid: float(mr.score)
                    for mid, mr in ev.metric_results.items()
                    if mr.score is not None and not mr.skipped
                },
                "latency_ms": None,
                "cost_usd": None,
            }
        )

    by_agent: dict[str, list[float]] = defaultdict(list)
    for row in evaluations:
        if row["overall_score"] is not None:
            by_agent[row["agent_id"]].append(float(row["overall_score"]))
    leaderboard = [
        {
            "agent_id": aid,
            "overall_score": sum(vals) / len(vals),
            "group_scores": {},
            "confidence": 0.0,
            "cost_usd": 0.0,
            "latency_ms": 0.0,
            "success_rate": 1.0,
            "n_trials": len(vals),
        }
        for aid, vals in by_agent.items()
    ]

    exp_ids = list(request.experiment_ids) or [summary.run_id]
    return ReportDocument(
        report_type=request.report_type,
        title=_title_for(request.report_type, exp_ids),
        experiment_ids=exp_ids,
        generated_at=datetime.now(UTC).isoformat(),
        brand=request.brand or BrandConfig(),
        leaderboard=leaderboard,
        evaluations=evaluations,
        recommendations=list(summary.recommendations),
        overview={
            "run_id": summary.run_id,
            "seed": summary.seed,
            "agent_ids": [str(a) for a in summary.agent_ids],
            "task_ids": list(summary.task_ids),
            "overall_scores": dict(summary.overall_scores),
            "group_scores": dict(summary.group_scores),
        },
        appendix={
            "package_version": __version__,
            "source": "run_summary",
            "methodology_metrics": [
                {"metric_id": mid, "group": get_metric_group(mid).value}
                for mid in METHODOLOGY_METRIC_IDS
            ],
        },
        metadata={"seed": summary.seed, "from_run_summary": True},
    )


def resolve_output_dir(request: ReportRequest) -> Path:
    if request.output_dir is not None:
        out = Path(request.output_dir)
    else:
        cfg = load_config()
        out = Path(cfg.runtime.paths.reports)
    out.mkdir(parents=True, exist_ok=True)
    return out
