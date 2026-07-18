"""Experiment / agent / dataset / prompt diff and regression detection."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.config import METHODOLOGY_METRIC_IDS
from githubbench_delta.dashboard.aggregations import build_leaderboard, build_task_rows
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.reports.models import DiffResult, MetricDelta

ABS_THRESHOLD = 0.05
REL_THRESHOLD = 0.10


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _delta(baseline: float | None, candidate: float | None) -> MetricDelta:
    if baseline is None or candidate is None:
        return MetricDelta(key="", baseline=baseline, candidate=candidate)
    delta = candidate - baseline
    relative = (delta / abs(baseline)) if baseline != 0 else None
    is_reg = False
    if delta <= -ABS_THRESHOLD:
        is_reg = True
    if relative is not None and relative <= -REL_THRESHOLD:
        is_reg = True
    return MetricDelta(
        key="",
        baseline=baseline,
        candidate=candidate,
        delta=delta,
        relative=relative,
        is_regression=is_reg,
    )


def _cost_latency_regression(baseline: float | None, candidate: float | None) -> MetricDelta:
    """Higher cost/latency is a regression."""

    d = _delta(baseline, candidate)
    if baseline is None or candidate is None:
        return d
    delta = candidate - baseline
    relative = (delta / abs(baseline)) if baseline != 0 else None
    is_reg = False
    if delta >= ABS_THRESHOLD:  # for cost in dollars; latency uses same relative
        is_reg = True
    if relative is not None and relative >= REL_THRESHOLD:
        is_reg = True
    # Latency often large absolute — prefer relative for ms
    return MetricDelta(
        key=d.key,
        baseline=baseline,
        candidate=candidate,
        delta=delta,
        relative=relative,
        is_regression=is_reg,
    )


def _meta_version(experiment: dict[str, Any], key: str) -> str | None:
    meta = experiment.get("metadata") or {}
    if isinstance(meta, dict) and meta.get(key):
        return str(meta[key])
    snap = experiment.get("config_snapshot") or {}
    if isinstance(snap, dict):
        if snap.get(key):
            return str(snap[key])
        for nest_key in ("dataset", "prompts", "prompt"):
            nested = snap.get(nest_key) or {}
            if isinstance(nested, dict):
                if nested.get(key):
                    return str(nested[key])
                if key.endswith("version") and nested.get("version"):
                    return str(nested["version"])
    return None


def _scope_rows(
    repo: ExperimentRepository,
    experiment_id: str,
    *,
    agent_id: str | None = None,
) -> list[Any]:
    rows = repo.all_evaluation_rows([experiment_id])
    if agent_id:
        rows = [r for r in rows if r.agent_id == agent_id]
    return rows


def _trajectory_stats(repo: ExperimentRepository, experiment_id: str) -> dict[str, float]:
    items = repo.list_trajectories(experiment_id)
    if not items:
        return {"mean_steps": 0.0, "n": 0.0, "error_rate": 0.0, "tool_calls": 0.0}
    steps = [float(i.step_count) for i in items]
    error_steps = 0
    tool_calls = 0
    total_steps = 0
    for item in items[:50]:
        detail = repo.get_trajectory(experiment_id, item.unit_key)
        if not detail:
            continue
        for step in detail.steps or []:
            total_steps += 1
            kind = (step.get("kind") or "").lower()
            if kind in {"error", "warning"}:
                error_steps += 1
            tc = step.get("tool_call") or {}
            if tc.get("name"):
                tool_calls += 1
    return {
        "mean_steps": float(_mean(steps) or 0.0),
        "n": float(len(items)),
        "error_rate": (error_steps / total_steps) if total_steps else 0.0,
        "tool_calls": float(tool_calls),
    }


def compare_experiments(
    repo: ExperimentRepository,
    baseline_id: str,
    candidate_id: str,
    *,
    agent_baseline: str | None = None,
    agent_candidate: str | None = None,
    compare_kind: str = "experiment",
) -> DiffResult:
    """Compare two experiment scopes and flag regressions."""

    notes: list[str] = []
    b_detail = repo.get_experiment(baseline_id)
    c_detail = repo.get_experiment(candidate_id)
    if b_detail is None:
        notes.append(f"Baseline experiment not found: {baseline_id}")
    if c_detail is None:
        notes.append(f"Candidate experiment not found: {candidate_id}")

    b_exp = b_detail.experiment if b_detail else {}
    c_exp = c_detail.experiment if c_detail else {}

    ds_b = _meta_version(b_exp, "dataset_version")
    ds_c = _meta_version(c_exp, "dataset_version")
    pv_b = _meta_version(b_exp, "prompt_version")
    pv_c = _meta_version(c_exp, "prompt_version")
    if ds_b is None and ds_c is None:
        notes.append("Dataset version metadata missing on one or both experiments.")
    if pv_b is None and pv_c is None:
        notes.append("Prompt version metadata missing on one or both experiments.")
    if ds_b != ds_c and (ds_b or ds_c):
        compare_kind = "dataset_version" if compare_kind == "experiment" else compare_kind
    if pv_b != pv_c and (pv_b or pv_c):
        if compare_kind == "experiment":
            compare_kind = "prompt_version"

    b_rows = _scope_rows(repo, baseline_id, agent_id=agent_baseline)
    c_rows = _scope_rows(repo, candidate_id, agent_id=agent_candidate)

    b_overall = _mean([float(r.overall_score) for r in b_rows if r.overall_score is not None])
    c_overall = _mean([float(r.overall_score) for r in c_rows if r.overall_score is not None])
    overall = _delta(b_overall, c_overall)
    overall.key = "overall_score"

    # Metric means
    metric_deltas: list[MetricDelta] = []
    for mid in METHODOLOGY_METRIC_IDS:
        bv = _mean([float(r.metric_scores[mid]) for r in b_rows if mid in r.metric_scores])
        cv = _mean([float(r.metric_scores[mid]) for r in c_rows if mid in r.metric_scores])
        d = _delta(bv, cv)
        d.key = mid
        if bv is not None or cv is not None:
            metric_deltas.append(d)

    # Group means from leaderboard
    b_board, _ = build_leaderboard(
        repo, experiment_ids=[baseline_id], agent_id=agent_baseline, page_size=100
    )
    c_board, _ = build_leaderboard(
        repo, experiment_ids=[candidate_id], agent_id=agent_candidate, page_size=100
    )

    def _avg_group(board: list[Any], group: str) -> float | None:
        vals = [float(row.group_scores[group]) for row in board if group in row.group_scores]
        return _mean(vals)

    groups = sorted({g for row in list(b_board) + list(c_board) for g in row.group_scores})
    group_deltas = []
    for g in groups:
        d = _delta(_avg_group(b_board, g), _avg_group(c_board, g))
        d.key = g
        group_deltas.append(d)

    # Task deltas
    b_tasks, _ = build_task_rows(repo, experiment_ids=[baseline_id], page_size=500)
    c_tasks, _ = build_task_rows(repo, experiment_ids=[candidate_id], page_size=500)
    b_map = {t.task_id: t.mean_score for t in b_tasks}
    c_map = {t.task_id: t.mean_score for t in c_tasks}
    task_deltas = []
    for tid in sorted(set(b_map) | set(c_map)):
        d = _delta(b_map.get(tid), c_map.get(tid))
        d.key = tid
        task_deltas.append(d)

    b_cost = _mean([float(r.cost_usd) for r in b_rows if r.cost_usd is not None])
    c_cost = _mean([float(r.cost_usd) for r in c_rows if r.cost_usd is not None])
    cost_delta = _cost_latency_regression(b_cost, c_cost)
    cost_delta.key = "cost_usd"

    b_lat = _mean([float(r.latency_ms) for r in b_rows if r.latency_ms is not None])
    c_lat = _mean([float(r.latency_ms) for r in c_rows if r.latency_ms is not None])
    # Latency: relative increase is regression
    lat_d = _delta(b_lat, c_lat)
    if b_lat is not None and c_lat is not None:
        delta = c_lat - b_lat
        relative = (delta / abs(b_lat)) if b_lat != 0 else None
        lat_d = MetricDelta(
            key="latency_ms",
            baseline=b_lat,
            candidate=c_lat,
            delta=delta,
            relative=relative,
            is_regression=bool(
                (relative is not None and relative >= REL_THRESHOLD) or delta >= 500.0
            ),
        )
    else:
        lat_d.key = "latency_ms"

    traj_b = _trajectory_stats(repo, baseline_id)
    traj_c = _trajectory_stats(repo, candidate_id)
    trajectory_deltas = []
    for key in ("mean_steps", "error_rate", "tool_calls"):
        # Increases in steps/errors/tools are treated as regressions when relative high
        d = _cost_latency_regression(traj_b.get(key), traj_c.get(key))
        d.key = key
        # For error_rate use absolute 0.05
        if key == "error_rate" and d.delta is not None:
            d.is_regression = d.delta >= ABS_THRESHOLD
        trajectory_deltas.append(d)

    if agent_baseline or agent_candidate:
        compare_kind = "agent"

    return DiffResult(
        baseline_id=baseline_id,
        candidate_id=candidate_id,
        compare_kind=compare_kind,
        notes=notes,
        overall_delta=overall,
        metric_deltas=metric_deltas,
        group_deltas=group_deltas,
        task_deltas=task_deltas,
        cost_delta=cost_delta,
        latency_delta=lat_d,
        trajectory_deltas=trajectory_deltas,
        dataset_version_baseline=ds_b,
        dataset_version_candidate=ds_c,
        prompt_version_baseline=pv_b,
        prompt_version_candidate=pv_c,
        agent_baseline=agent_baseline,
        agent_candidate=agent_candidate,
    )


def compare_agents(
    repo: ExperimentRepository,
    experiment_id: str,
    agent_a: str,
    agent_b: str,
) -> DiffResult:
    """Compare two agents within the same experiment (A=baseline, B=candidate)."""

    return compare_experiments(
        repo,
        experiment_id,
        experiment_id,
        agent_baseline=agent_a,
        agent_candidate=agent_b,
        compare_kind="agent",
    )
