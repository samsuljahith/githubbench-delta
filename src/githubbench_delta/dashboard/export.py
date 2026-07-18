"""CSV / JSON / Markdown exporters for dashboard exploration."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from githubbench_delta.dashboard.aggregations import build_leaderboard, build_overview
from githubbench_delta.dashboard.repository import ExperimentRepository


def export_json(repo: ExperimentRepository, *, experiment_id: str | None = None) -> str:
    ids = [experiment_id] if experiment_id else None
    board, _ = build_leaderboard(repo, experiment_ids=ids, page_size=500)
    rows = repo.all_evaluation_rows(ids)
    payload: dict[str, Any] = {
        "overview": build_overview(repo).model_dump(mode="json"),
        "leaderboard": [b.model_dump(mode="json") for b in board],
        "evaluations": [r.model_dump(mode="json") for r in rows],
    }
    if experiment_id:
        detail = repo.get_experiment(experiment_id)
        payload["experiment"] = detail.model_dump(mode="json") if detail else None
    return json.dumps(payload, indent=2, sort_keys=True)


def export_csv(repo: ExperimentRepository, *, experiment_id: str | None = None) -> str:
    ids = [experiment_id] if experiment_id else None
    rows = repo.all_evaluation_rows(ids)
    buf = io.StringIO()
    fieldnames = [
        "experiment_id",
        "task_id",
        "agent_id",
        "trial_index",
        "overall_score",
        "confidence_score",
        "success",
        "category",
        "latency_ms",
        "cost_usd",
    ]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r.model_dump())
    return buf.getvalue()


def export_markdown(repo: ExperimentRepository, *, experiment_id: str | None = None) -> str:
    ids = [experiment_id] if experiment_id else None
    board, _ = build_leaderboard(repo, experiment_ids=ids, page_size=100)
    lines = ["# GitHubBench-Delta Export", ""]
    if experiment_id:
        detail = repo.get_experiment(experiment_id)
        if detail:
            lines.append(f"## Experiment `{experiment_id}`")
            lines.append("")
            lines.append(f"- Status: `{detail.experiment.get('status')}`")
            lines.append(f"- Agents: {', '.join(detail.experiment.get('agent_ids') or [])}")
            lines.append(f"- Mean overall: {detail.summary.get('mean_overall_score')}")
            lines.append("")
    lines.append("## Leaderboard")
    lines.append("")
    lines.append("| Agent | Overall | Confidence | Success | Cost | Latency | N |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for b in board:
        lines.append(
            f"| {b.agent_id} | {b.overall_score:.3f} | {b.confidence:.3f} | "
            f"{b.success_rate:.3f} | {b.cost_usd:.4f} | {b.latency_ms:.1f} | {b.n_trials} |"
        )
    lines.append("")
    return "\n".join(lines)


def export(
    format: str,
    repo: ExperimentRepository,
    *,
    experiment_id: str | None = None,
) -> tuple[str, str]:
    """Return (media_type, body)."""

    fmt = format.lower()
    if fmt == "json":
        return "application/json", export_json(repo, experiment_id=experiment_id)
    if fmt == "csv":
        return "text/csv", export_csv(repo, experiment_id=experiment_id)
    if fmt in {"md", "markdown"}:
        return "text/markdown", export_markdown(repo, experiment_id=experiment_id)
    raise ValueError(f"Unsupported export format: {format}")
