"""Plotly figure builders for dashboard charts."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from githubbench_delta.dashboard.aggregations import (
    build_agent_compare,
    build_correlation,
    build_leaderboard,
    build_metric_stats,
)
from githubbench_delta.dashboard.repository import ExperimentRepository


def _fig_json(fig: go.Figure) -> dict[str, Any]:
    return fig.to_plotly_json()


def radar_chart(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
) -> dict[str, Any]:
    cmp = build_agent_compare(repo, experiment_ids=experiment_ids)
    fig = go.Figure()
    # Union of group keys
    groups: list[str] = sorted({g for scores in cmp.group_scores.values() for g in scores})
    if not groups:
        groups = ["correctness", "trajectory", "safety", "grounding", "reliability", "efficiency"]
    for agent in cmp.agents:
        scores = cmp.group_scores.get(agent, {})
        values = [float(scores.get(g, 0.0)) for g in groups]
        values.append(values[0] if values else 0.0)
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=groups + ([groups[0]] if groups else []),
                fill="toself",
                name=agent,
            )
        )
    fig.update_layout(
        title="Agent comparison (group scores)",
        polar={"radialaxis": {"visible": True, "range": [0, 1]}},
        showlegend=True,
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return _fig_json(fig)


def bars_chart(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
) -> dict[str, Any]:
    board, _ = build_leaderboard(repo, experiment_ids=experiment_ids, page_size=100)
    fig = go.Figure(
        data=[
            go.Bar(
                x=[b.agent_id for b in board],
                y=[b.overall_score for b in board],
                name="Overall",
            )
        ]
    )
    fig.update_layout(
        title="Overall score by agent",
        yaxis={"range": [0, 1]},
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return _fig_json(fig)


def histogram_chart(
    repo: ExperimentRepository,
    *,
    metric_id: str = "task_resolution",
    experiment_ids: list[str] | None = None,
) -> dict[str, Any]:
    stats = {s.metric_id: s for s in build_metric_stats(repo, experiment_ids=experiment_ids)}
    stat = stats.get(metric_id)
    if not stat or not stat.histogram:
        fig = go.Figure()
        fig.update_layout(title=f"Histogram: {metric_id} (no data)")
        return _fig_json(fig)
    # Bin midpoints for x
    edges = stat.histogram_bins
    mids = (
        [(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)]
        if len(edges) > 1
        else list(range(len(stat.histogram)))
    )
    fig = go.Figure(data=[go.Bar(x=mids, y=stat.histogram, name=metric_id)])
    fig.update_layout(
        title=f"Score distribution: {metric_id}",
        xaxis_title="Score",
        yaxis_title="Count",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    return _fig_json(fig)


def corr_heatmap(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
) -> dict[str, Any]:
    corr = build_correlation(repo, experiment_ids=experiment_ids)
    fig = go.Figure(
        data=go.Heatmap(
            z=corr.matrix,
            x=corr.metrics,
            y=corr.metrics,
            colorscale="RdBu",
            zmin=-1,
            zmax=1,
        )
    )
    fig.update_layout(
        title="Metric correlation matrix",
        margin=dict(l=80, r=40, t=50, b=80),
        height=700,
    )
    return _fig_json(fig)


def timeline_chart(
    repo: ExperimentRepository,
    *,
    experiment_id: str,
    unit_key: str,
) -> dict[str, Any]:
    detail = repo.get_trajectory(experiment_id, unit_key)
    fig = go.Figure()
    if not detail:
        fig.update_layout(title="Trajectory timeline (not found)")
        return _fig_json(fig)
    labels = []
    ys = []
    texts = []
    for i, step in enumerate(detail.steps):
        kind = step.get("kind") or "step"
        name = ""
        if step.get("tool_call"):
            name = step["tool_call"].get("name", "")
        labels.append(f"{i}:{kind}" + (f"/{name}" if name else ""))
        ys.append(i)
        texts.append((step.get("content") or step.get("error") or "")[:120])
    fig.add_trace(
        go.Scatter(
            x=ys,
            y=[1] * len(ys),
            mode="markers+text",
            text=labels,
            textposition="top center",
            customdata=texts,
            hovertemplate="%{text}<br>%{customdata}<extra></extra>",
            marker={"size": 12},
        )
    )
    fig.update_layout(
        title=f"Timeline: {unit_key}",
        xaxis_title="Step",
        yaxis={"visible": False},
        margin=dict(l=40, r=40, t=50, b=40),
        height=280,
    )
    return _fig_json(fig)


def importance_bars(
    repo: ExperimentRepository,
    *,
    experiment_ids: list[str] | None = None,
) -> dict[str, Any]:
    stats = build_metric_stats(repo, experiment_ids=experiment_ids)
    stats = sorted(stats, key=lambda s: s.importance, reverse=True)
    fig = go.Figure(
        data=[
            go.Bar(
                x=[s.metric_id for s in stats],
                y=[s.importance for s in stats],
                name="importance",
            )
        ]
    )
    fig.update_layout(
        title="Metric importance (normalized variance)",
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=50, b=120),
    )
    return _fig_json(fig)


CHART_BUILDERS = {
    "radar": radar_chart,
    "bars": bars_chart,
    "histogram": histogram_chart,
    "corr_heatmap": corr_heatmap,
    "timeline": timeline_chart,
    "importance": importance_bars,
}


def build_chart(
    name: str,
    repo: ExperimentRepository,
    **kwargs: Any,
) -> dict[str, Any]:
    builder = CHART_BUILDERS.get(name)
    if builder is None:
        raise KeyError(f"Unknown chart: {name}")
    return builder(repo, **kwargs)
