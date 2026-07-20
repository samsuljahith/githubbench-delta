"""Plotly chart builders for Half-Life Observatory."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from githubbench_delta.observatory.models import HalfLifeEstimate, TrendReport

logger = logging.getLogger(__name__)


def _layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_white",
        margin=dict(l=48, r=24, t=56, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def score_vs_time_figure(trends: TrendReport) -> go.Figure:
    fig = go.Figure()
    by_label: dict[str, list] = {}
    for pt in trends.score_vs_time:
        by_label.setdefault(pt.label or "agent", []).append(pt)
    for label, pts in sorted(by_label.items()):
        fig.add_trace(
            go.Scatter(
                x=[p.timestamp for p in pts],
                y=[p.value for p in pts],
                mode="lines+markers",
                name=label,
            )
        )
    return _layout(fig, "Score vs time")


def provider_trend_figure(trends: TrendReport) -> go.Figure:
    fig = go.Figure()
    for provider, pts in sorted(trends.provider_trends.items()):
        # Aggregate mean score per timestamp for provider
        buckets: dict[str, list[float]] = {}
        ts_map: dict[str, Any] = {}
        for p in pts:
            key = p.timestamp.isoformat()
            buckets.setdefault(key, []).append(p.value)
            ts_map[key] = p.timestamp
        keys = sorted(buckets.keys())
        fig.add_trace(
            go.Scatter(
                x=[ts_map[k] for k in keys],
                y=[sum(buckets[k]) / len(buckets[k]) for k in keys],
                mode="lines+markers",
                name=provider,
            )
        )
    return _layout(fig, "Provider mean score vs time")


def model_progression_figure(trends: TrendReport) -> go.Figure:
    fig = go.Figure()
    for model, pts in sorted(trends.model_progression.items()):
        fig.add_trace(
            go.Scatter(
                x=[p.timestamp for p in pts],
                y=[p.value for p in pts],
                mode="lines+markers",
                name=model,
            )
        )
    return _layout(fig, "Model progression")


def saturation_figure(trends: TrendReport) -> go.Figure:
    fig = go.Figure()
    pts = trends.saturation_vs_time
    fig.add_trace(
        go.Scatter(
            x=[p.timestamp for p in pts],
            y=[p.value for p in pts],
            mode="lines+markers",
            name="saturation S(t)",
            line=dict(color="#c45c26"),
        )
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color="#888", annotation_text="ceiling")
    return _layout(fig, "Saturation vs time")


def differentiation_curve_figure(estimate: HalfLifeEstimate) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    pts = estimate.decay_curve.points
    fig.add_trace(
        go.Scatter(
            x=[p.t_days for p in pts],
            y=[p.differentiation for p in pts],
            mode="markers",
            name="D(t) observed",
            marker=dict(size=10),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=[p.t_days for p in pts],
            y=[p.fitted for p in pts],
            mode="lines",
            name="D(t) fitted",
            line=dict(dash="dash"),
        ),
        secondary_y=False,
    )
    if estimate.saturation_series:
        fig.add_trace(
            go.Scatter(
                x=[p.t_days for p in estimate.saturation_series],
                y=[p.saturation for p in estimate.saturation_series],
                mode="lines+markers",
                name="S(t)",
                line=dict(color="#c45c26"),
            ),
            secondary_y=True,
        )
    fig.update_xaxes(title_text="Days since first cohort")
    fig.update_yaxes(title_text="Differentiation D(t)", secondary_y=False)
    fig.update_yaxes(title_text="Saturation S(t)", secondary_y=True)
    hl = estimate.half_life_days
    title = "Differentiation decay"
    if hl is not None:
        title += f" (t½ ≈ {hl:.1f} days, conf={estimate.confidence:.2f})"
    else:
        title += f" (non-decaying, conf={estimate.confidence:.2f})"
    return _layout(fig, title)


def write_figure(
    fig: go.Figure,
    out_dir: Path,
    name: str,
    *,
    write_png: bool = True,
) -> dict[str, Path]:
    """Write HTML (always) and PNG (when Kaleido available)."""

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    html_path = out_dir / f"{name}.html"
    fig.write_html(str(html_path), include_plotlyjs="cdn", full_html=True)
    paths["html"] = html_path
    if write_png:
        png_path = out_dir / f"{name}.png"
        try:
            import plotly.io as pio

            pio.write_image(fig, str(png_path), format="png", width=960, height=540, scale=2)
            paths["png"] = png_path
        except Exception as exc:  # noqa: BLE001 — PNG is optional
            logger.warning("PNG export for %s failed: %s", name, exc)
    return paths


def write_all_charts(
    trends: TrendReport,
    estimate: HalfLifeEstimate,
    charts_dir: Path,
    *,
    write_png: bool = True,
) -> dict[str, dict[str, Path]]:
    builders: dict[str, go.Figure] = {
        "score_vs_time": score_vs_time_figure(trends),
        "provider_trend": provider_trend_figure(trends),
        "model_progression": model_progression_figure(trends),
        "saturation": saturation_figure(trends),
        "differentiation_curve": differentiation_curve_figure(estimate),
    }
    written: dict[str, dict[str, Path]] = {}
    for name, fig in builders.items():
        written[name] = write_figure(fig, charts_dir, name, write_png=write_png)
    return written
