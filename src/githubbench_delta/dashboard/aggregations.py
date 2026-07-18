"""Deterministic dashboard aggregations over evaluation rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from githubbench_delta.core.config import METHODOLOGY_METRIC_IDS
from githubbench_delta.dashboard.repository import (
    ExperimentRepository,
    _mean,
    _paginate,
    _sort_rows,
)
from githubbench_delta.dashboard.schemas import (
    AgentCompareResponse,
    CorrelationResponse,
    LeaderboardRow,
    MetricStat,
    OverviewResponse,
    TaskRow,
)


def build_leaderboard(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
    agent_id: str | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort: str = "overall_score",
    order: str = "desc",
) -> tuple[list[LeaderboardRow], int]:
    rows = repo.all_evaluation_rows(experiment_ids)
    if agent_id:
        rows = [r for r in rows if r.agent_id == agent_id]
    if category:
        rows = [r for r in rows if r.category == category]

    by_agent: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        by_agent[r.agent_id].append(r)

    board: list[LeaderboardRow] = []
    for aid, items in by_agent.items():
        overalls = [float(i.overall_score) for i in items if i.overall_score is not None]
        confs = [float(i.confidence_score) for i in items if i.confidence_score is not None]
        costs = [float(i.cost_usd) for i in items if i.cost_usd is not None]
        lats = [float(i.latency_ms) for i in items if i.latency_ms is not None]
        successes = [1.0 for i in items if i.success is True]
        group_acc: dict[str, list[float]] = defaultdict(list)
        for i in items:
            for g, s in i.group_scores.items():
                group_acc[g].append(float(s))
        board.append(
            LeaderboardRow(
                agent_id=aid,
                overall_score=_mean(overalls) or 0.0,
                group_scores={g: (_mean(v) or 0.0) for g, v in group_acc.items()},
                confidence=_mean(confs) or 0.0,
                cost_usd=_mean(costs) or 0.0,
                latency_ms=_mean(lats) or 0.0,
                success_rate=(len(successes) / len(items)) if items else 0.0,
                n_trials=len(items),
            )
        )
    as_dicts = [b.model_dump() for b in board]
    as_dicts = _sort_rows(as_dicts, sort=sort, order=order)
    page_items, total = _paginate(as_dicts, page=page, page_size=page_size)
    return [LeaderboardRow.model_validate(x) for x in page_items], total


def build_agent_compare(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
) -> AgentCompareResponse:
    board, _ = build_leaderboard(repo, experiment_ids=experiment_ids, page=1, page_size=100)
    agents = [b.agent_id for b in board]
    group_scores = {b.agent_id: b.group_scores for b in board}
    metric_means: dict[str, dict[str, float]] = defaultdict(dict)
    rows = repo.all_evaluation_rows(experiment_ids)
    by_agent: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        by_agent[r.agent_id].append(r)
    for aid, items in by_agent.items():
        for mid in METHODOLOGY_METRIC_IDS:
            vals = [float(i.metric_scores[mid]) for i in items if mid in i.metric_scores]
            if vals:
                metric_means[aid][mid] = float(_mean(vals) or 0.0)
    return AgentCompareResponse(
        agents=agents,
        group_scores=group_scores,
        metric_means=dict(metric_means),
        leaderboard=board,
    )


def build_task_rows(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
    category: str | None = None,
    language: str | None = None,
    difficulty: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort: str = "mean_score",
    order: str = "desc",
) -> tuple[list[TaskRow], int]:
    ids = experiment_ids or repo.list_experiment_ids()
    task_meta: dict[str, dict[str, Any]] = {}
    for eid in ids:
        manifest = repo.load_experiment_manifest(eid) or {}
        ds = manifest.get("dataset_path")
        if ds:
            task_meta.update(repo.load_task_metadata(ds))

    rows = repo.all_evaluation_rows(ids)
    by_task: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        by_task[r.task_id].append(r)

    tasks: list[TaskRow] = []
    for tid, items in by_task.items():
        meta = task_meta.get(tid, {})
        cat = meta.get("category") or (items[0].category if items else None)
        diff = meta.get("difficulty")
        lang = meta.get("language")
        if category and cat != category:
            continue
        if language and lang != language:
            continue
        if difficulty and diff != difficulty:
            continue
        if q and q.lower() not in tid.lower():
            continue
        scores = [float(i.overall_score) for i in items if i.overall_score is not None]
        tasks.append(
            TaskRow(
                task_id=tid,
                category=cat,
                difficulty=diff,
                language=lang,
                repository=meta.get("repository"),
                mean_score=_mean(scores),
                n_evals=len(items),
                agents=sorted({i.agent_id for i in items}),
            )
        )
    as_dicts = [t.model_dump() for t in tasks]
    as_dicts = _sort_rows(as_dicts, sort=sort, order=order)
    page_items, total = _paginate(as_dicts, page=page, page_size=page_size)
    return [TaskRow.model_validate(x) for x in page_items], total


def metric_matrix_frame(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
) -> pd.DataFrame:
    rows = repo.all_evaluation_rows(experiment_ids)
    records: list[dict[str, float]] = []
    for r in rows:
        rec = {mid: r.metric_scores.get(mid) for mid in METHODOLOGY_METRIC_IDS}
        if any(v is not None for v in rec.values()):
            records.append({k: float(v) for k, v in rec.items() if v is not None})
    if not records:
        return pd.DataFrame(columns=list(METHODOLOGY_METRIC_IDS))
    return pd.DataFrame(records).reindex(columns=list(METHODOLOGY_METRIC_IDS))


def build_metric_stats(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
    bins: int = 10,
) -> list[MetricStat]:
    df = metric_matrix_frame(repo, experiment_ids=experiment_ids)
    raw_stats: list[tuple[MetricStat, float]] = []
    for mid in METHODOLOGY_METRIC_IDS:
        series = df[mid].dropna() if mid in df.columns else pd.Series(dtype=float)
        if series.empty:
            raw_stats.append((MetricStat(metric_id=mid), 0.0))
            continue
        var = float(series.var(ddof=0) or 0.0)
        counts: list[int] = []
        edges: list[float] = []
        try:
            if float(series.nunique()) <= 1:
                counts = [int(series.count())]
                edges = [float(series.min()) - 1e-9, float(series.max()) + 1e-9]
            else:
                hist, bin_edges = pd.cut(series, bins=bins, retbins=True, include_lowest=True)
                counts = [int(c) for c in hist.value_counts(sort=False).tolist()]
                edges = [float(x) for x in bin_edges]
        except ValueError:
            counts = [int(series.count())]
            edges = [float(series.min()), float(series.max())]
        raw_stats.append(
            (
                MetricStat(
                    metric_id=mid,
                    mean=float(series.mean()),
                    std=float(series.std(ddof=0) or 0.0),
                    min=float(series.min()),
                    max=float(series.max()),
                    n=int(series.count()),
                    histogram=counts,
                    histogram_bins=edges,
                ),
                var,
            )
        )
    total_var = sum(v for _, v in raw_stats) or 1.0
    return [s.model_copy(update={"importance": var / total_var}) for s, var in raw_stats]


def build_correlation(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
) -> CorrelationResponse:
    df = metric_matrix_frame(repo, experiment_ids=experiment_ids)
    metrics = list(METHODOLOGY_METRIC_IDS)
    if df.empty or len(df) < 2:
        n = len(metrics)
        identity = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        return CorrelationResponse(metrics=metrics, matrix=identity)
    corr = df.corr(method="pearson").reindex(index=metrics, columns=metrics)
    corr = corr.fillna(0.0)
    matrix = corr.values.tolist()
    return CorrelationResponse(
        metrics=metrics,
        matrix=[[float(x) for x in row] for row in matrix],
    )


def build_overview(repo: ExperimentRepository) -> OverviewResponse:
    latest, _ = repo.list_experiments(page=1, page_size=5, sort="updated_at", order="desc")
    all_rows = repo.all_evaluation_rows()
    scores = [float(r.overall_score) for r in all_rows if r.overall_score is not None]
    agents = sorted({r.agent_id for r in all_rows})
    return OverviewResponse(
        experiment_count=len(repo.list_experiment_ids()),
        evaluation_count=len(all_rows),
        agent_ids=agents,
        latest_experiments=latest,
        mean_overall_score=_mean(scores),
    )
