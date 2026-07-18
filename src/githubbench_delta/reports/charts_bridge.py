"""Bridge to Phase 6 Plotly chart builders for report embedding."""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from githubbench_delta.dashboard.charts import build_chart
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.reports.models import ChartAsset, ReportDocument

logger = logging.getLogger(__name__)

DEFAULT_CHARTS = ("radar", "bars", "histogram", "corr_heatmap", "importance")


def collect_charts(
    repo: ExperimentRepository,
    doc: ReportDocument,
    *,
    assets_dir: Path | None = None,
    chart_names: tuple[str, ...] | None = None,
    write_png: bool = True,
) -> dict[str, ChartAsset]:
    """Build Plotly JSON (and optional PNG) for charts referenced by sections."""

    needed: set[str] = set()
    for section in doc.sections:
        needed.update(section.chart_ids)
    names = list(chart_names) if chart_names is not None else sorted(needed or DEFAULT_CHARTS)
    if not names:
        names = list(DEFAULT_CHARTS)

    exp_ids = doc.experiment_ids or None
    charts: dict[str, ChartAsset] = {}
    for name in names:
        try:
            fig_json = build_chart(name, repo, experiment_ids=exp_ids)
        except Exception as exc:  # noqa: BLE001 — chart failure must not abort report
            logger.warning("Chart %s failed: %s", name, exc)
            continue
        asset = ChartAsset(
            chart_id=name,
            title=name.replace("_", " ").title(),
            plotly_json=fig_json,
        )
        if write_png and assets_dir is not None:
            png_path = assets_dir / f"{name}.png"
            b64 = _write_png(fig_json, png_path)
            if b64:
                asset.png_relpath = f"_assets/{name}.png"
                asset.png_base64 = b64
        charts[name] = asset
    return charts


def _write_png(fig_json: dict[str, Any], path: Path) -> str | None:
    try:
        import plotly.graph_objects as go
        import plotly.io as pio

        fig = go.Figure(fig_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        pio.write_image(fig, str(path), format="png", width=900, height=500, scale=2)
        data = path.read_bytes()
        return base64.b64encode(data).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        logger.warning("PNG export for chart failed (%s): %s", path.name, exc)
        return None
