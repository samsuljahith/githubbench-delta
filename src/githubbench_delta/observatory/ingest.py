"""Ingest BenchmarkSnapshots from completed experiment artifacts."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from githubbench_delta import __version__
from githubbench_delta.core.config import load_config
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.observatory.history import BenchmarkHistory
from githubbench_delta.observatory.models import BenchmarkSnapshot, MetricSummary


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _parse_ts(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(UTC)
    text = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _agent_catalog() -> dict[str, dict[str, str]]:
    cfg = load_config()
    out: dict[str, dict[str, str]] = {}
    for agent_id, agent in cfg.agents.items():
        out[str(agent_id)] = {
            "provider": str(getattr(agent, "provider", agent_id) or agent_id),
            "model": str(getattr(agent, "model", agent_id) or agent_id),
        }
    return out


def _tool_usage_for_experiment(
    repo: ExperimentRepository,
    experiment_id: str,
) -> dict[str, list[float]]:
    by_agent: dict[str, list[float]] = defaultdict(list)
    for raw in repo._load_trajectory_raw(experiment_id):  # noqa: SLF001 — reuse reader
        agent_id = str(raw.get("agent_id", ""))
        ar = raw.get("agent_result") or {}
        metrics = ar.get("metrics") or {}
        if "tool_call_count" in metrics:
            by_agent[agent_id].append(float(metrics["tool_call_count"]))
    return by_agent


def snapshots_from_experiment(
    experiment_id: str,
    *,
    results_dir: Path | str | None = None,
) -> list[BenchmarkSnapshot]:
    """Build one snapshot per agent from a completed experiment directory."""

    repo = ExperimentRepository(results_dir=results_dir)
    manifest_path = repo.experiment_dir(experiment_id) / "experiment.json"
    if not manifest_path.is_file():
        return []
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    timestamp = _parse_ts(manifest.get("updated_at") or manifest.get("created_at"))
    dataset_path = str(manifest.get("dataset_path") or "")
    dataset_version = Path(dataset_path).name if dataset_path else "unknown"
    benchmark_version = f"{__version__}+{dataset_version}"
    catalog = _agent_catalog()
    tool_by_agent = _tool_usage_for_experiment(repo, experiment_id)
    rows = repo.evaluation_rows(experiment_id)
    if not rows:
        return []

    by_agent: dict[str, list] = defaultdict(list)
    for row in rows:
        by_agent[row.agent_id].append(row)

    snapshots: list[BenchmarkSnapshot] = []
    source = str(repo.experiment_dir(experiment_id))
    for agent_id, items in sorted(by_agent.items()):
        scores = [float(i.overall_score) for i in items if i.overall_score is not None]
        confs = [float(i.confidence_score) for i in items if i.confidence_score is not None]
        lats = [float(i.latency_ms) for i in items if i.latency_ms is not None]
        costs = [float(i.cost_usd) for i in items if i.cost_usd is not None]
        successes = [1.0 if i.success else 0.0 for i in items if i.success is not None]
        group_acc: dict[str, list[float]] = defaultdict(list)
        metric_acc: dict[str, list[float]] = defaultdict(list)
        for item in items:
            for g, v in (item.group_scores or {}).items():
                group_acc[g].append(float(v))
            for mid, v in (item.metric_scores or {}).items():
                metric_acc[mid].append(float(v))
        info = catalog.get(agent_id, {"provider": agent_id, "model": agent_id})
        snapshots.append(
            BenchmarkSnapshot(
                snapshot_id=f"snap_{uuid4().hex[:12]}",
                timestamp=timestamp,
                benchmark_version=benchmark_version,
                experiment_id=experiment_id,
                agent_id=agent_id,
                model=info["model"],
                provider=info["provider"],
                score=_mean(scores),
                latency_ms=_mean(lats),
                cost_usd=_mean(costs),
                tool_usage=_mean(tool_by_agent.get(agent_id, [])),
                task_count=len({i.task_id for i in items}),
                success_rate=_mean(successes) if successes else 0.0,
                metric_summary=MetricSummary(
                    group_scores={k: _mean(v) for k, v in group_acc.items()},
                    metric_means={k: _mean(v) for k, v in metric_acc.items()},
                    confidence=_mean(confs) if confs else None,
                ),
                source=source,
                metadata={
                    "n_trials": len(items),
                    "score_std": statistics.pstdev(scores) if len(scores) > 1 else 0.0,
                    "dataset_path": dataset_path,
                },
            )
        )
    return snapshots


def ingest_experiments(
    *,
    experiment_ids: list[str] | None = None,
    results_dir: Path | str | None = None,
    history_dir: Path | str | None = None,
) -> tuple[int, int]:
    """Ingest experiments into history. Returns (written, skipped)."""

    repo = ExperimentRepository(results_dir=results_dir)
    ids = experiment_ids or repo.list_experiment_ids()
    history = BenchmarkHistory(history_dir=history_dir)
    written = 0
    considered = 0
    for eid in ids:
        snaps = snapshots_from_experiment(eid, results_dir=repo.results_dir)
        considered += len(snaps)
        written += history.extend(snaps)
    return written, considered - written
