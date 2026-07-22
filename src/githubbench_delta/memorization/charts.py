"""Plotly charts for Memorization Discounted Scoring."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from githubbench_delta.memorization.models import MemorizationReport


def _layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_white",
        margin=dict(l=48, r=24, t=56, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def capability_vs_memorization_figure(report: MemorizationReport) -> go.Figure:
    fig = go.Figure()
    agents = [b.agent_id for b in report.breakdowns]
    fig.add_trace(
        go.Bar(
            name="Generalization G",
            x=agents,
            y=[b.generalization * 100 for b in report.breakdowns],
            marker_color="#2a6f7a",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Memorization lift L",
            x=agents,
            y=[b.memorization_lift * 100 for b in report.breakdowns],
            marker_color="#c45c26",
        )
    )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="Score components (×100)", range=[0, 110])
    return _layout(fig, "Capability vs memorization")


def twin_agreement_figure(report: MemorizationReport) -> go.Figure:
    fig = go.Figure()
    xs: list[float] = []
    ys: list[float] = []
    labels: list[str] = []
    for lift in report.lifts:
        for p in lift.pairs:
            if p.s_twin is None:
                continue
            xs.append(p.s_obs * 100)
            ys.append(p.s_twin * 100)
            labels.append(f"{p.agent_id}:{p.parent_task_id}")
    if xs:
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers",
                text=labels,
                name="pairs",
                marker=dict(size=10, color="#2a6f7a"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[0, 100],
                y=[0, 100],
                mode="lines",
                name="agreement line",
                line=dict(dash="dash", color="#888"),
            )
        )
    else:
        fig.add_annotation(
            text="No twin pairs (proxy mode)",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
    fig.update_xaxes(title_text="Parent S_obs (×100)", range=[0, 100])
    fig.update_yaxes(title_text="Twin S_twin (×100)", range=[0, 100])
    return _layout(fig, "Twin task agreement")


def lift_distribution_figure(report: MemorizationReport) -> go.Figure:
    fig = go.Figure()
    for lift in report.lifts:
        vals = [p.lift * 100 for p in lift.pairs]
        if vals:
            fig.add_trace(go.Histogram(name=lift.agent_id, x=vals, opacity=0.75, nbinsx=12))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="Memorization lift L (×100)")
    fig.update_yaxes(title_text="Count")
    return _layout(fig, "Memorization lift distribution")


def posterior_ci_figure(report: MemorizationReport) -> go.Figure:
    fig = go.Figure()
    agents = [p.agent_id for p in report.posteriors]
    means = [p.mean * 100 for p in report.posteriors]
    err_plus = [max(0.0, (p.upper - p.mean) * 100) for p in report.posteriors]
    err_minus = [max(0.0, (p.mean - p.lower) * 100) for p in report.posteriors]
    fig.add_trace(
        go.Scatter(
            x=agents,
            y=means,
            mode="markers",
            name="posterior mean L",
            error_y=dict(
                type="data",
                symmetric=False,
                array=err_plus,
                arrayminus=err_minus,
            ),
            marker=dict(size=12, color="#2a6f7a"),
        )
    )
    fig.update_yaxes(title_text="Lift posterior (×100)", range=[0, 100])
    level = report.posteriors[0].level if report.posteriors else 0.95
    return _layout(fig, f"Posterior {int(level * 100)}% credible intervals for L")


def write_figure(fig: go.Figure, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.html"
    fig.write_html(str(path), include_plotlyjs="cdn", full_html=True)
    return path


def write_all_charts(report: MemorizationReport, charts_dir: Path) -> dict[str, Path]:
    builders = {
        "capability_vs_memorization": capability_vs_memorization_figure(report),
        "twin_agreement": twin_agreement_figure(report),
        "lift_distribution": lift_distribution_figure(report),
        "posterior_ci": posterior_ci_figure(report),
    }
    return {name: write_figure(fig, charts_dir, name) for name, fig in builders.items()}


def figures_as_div_html(report: MemorizationReport) -> dict[str, str]:
    builders = {
        "capability_vs_memorization": capability_vs_memorization_figure(report),
        "twin_agreement": twin_agreement_figure(report),
        "lift_distribution": lift_distribution_figure(report),
        "posterior_ci": posterior_ci_figure(report),
    }
    return {
        name: fig.to_html(full_html=False, include_plotlyjs=False) for name, fig in builders.items()
    }
