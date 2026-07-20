"""Unit tests for Half-Life Observatory (synthetic history only)."""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from githubbench_delta.cli import app as cli_app
from githubbench_delta.observatory.decay import DecayModel
from githubbench_delta.observatory.export import ObservatoryExporter
from githubbench_delta.observatory.half_life import HalfLifeEstimator, cohort_series
from githubbench_delta.observatory.history import BenchmarkHistory
from githubbench_delta.observatory.models import BenchmarkSnapshot, MetricSummary
from githubbench_delta.observatory.regression import RegressionDetector
from githubbench_delta.observatory.trends import TrendAnalyzer

runner = CliRunner()


def _snap(
    *,
    eid: str,
    agent: str,
    score: float,
    ts: datetime,
    provider: str = "local",
    model: str | None = None,
) -> BenchmarkSnapshot:
    return BenchmarkSnapshot(
        snapshot_id=f"snap_{eid}_{agent}",
        timestamp=ts,
        benchmark_version="0.1.0+test",
        experiment_id=eid,
        agent_id=agent,
        model=model or agent,
        provider=provider,
        score=score,
        latency_ms=1000.0,
        cost_usd=0.0,
        tool_usage=2.0,
        task_count=6,
        success_rate=1.0,
        metric_summary=MetricSummary(group_scores={"correctness": score}),
        source="synthetic",
    )


def _decaying_history(t0: datetime | None = None) -> list[BenchmarkSnapshot]:
    """Synthetic cohorts with shrinking score gap (differentiation decay)."""

    base = t0 or datetime(2025, 1, 1, tzinfo=UTC)
    # Gaps: 0.40, 0.28, 0.20, 0.14, 0.10  (~exponential)
    gaps = [0.40, 0.28, 0.20, 0.14, 0.10]
    mid = 0.55
    snaps: list[BenchmarkSnapshot] = []
    for i, gap in enumerate(gaps):
        ts = base + timedelta(days=30 * i)
        eid = f"exp_syn_{i:02d}"
        snaps.append(
            _snap(
                eid=eid,
                agent="weak",
                score=mid - gap / 2,
                ts=ts,
                provider="local",
                model="weak-model",
            )
        )
        snaps.append(
            _snap(
                eid=eid,
                agent="strong",
                score=mid + gap / 2,
                ts=ts,
                provider="hosted",
                model="strong-model",
            )
        )
    return snaps


def test_history_idempotent_append(tmp_path: Path) -> None:
    hist = BenchmarkHistory(history_dir=tmp_path)
    snaps = _decaying_history()[:2]
    assert hist.extend(snaps) == 2
    assert hist.extend(snaps) == 0
    assert len(hist.load()) == 2
    summary = hist.summary()
    assert summary["count"] == 2


def test_decay_model_recovers_half_life() -> None:
    # Exact exponential: D(t) = 0.4 * exp(-ln2/60 * t) → half-life 60 days
    lam = math.log(2) / 60.0
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    timestamps = [t0 + timedelta(days=d) for d in (0, 30, 60, 90, 120)]
    diffs = [0.4 * math.exp(-lam * d) for d in (0, 30, 60, 90, 120)]
    curve = DecayModel().fit(timestamps, diffs, saturation=[0.5] * 5)
    hl = DecayModel().half_life_days(curve)
    assert hl is not None
    assert abs(hl - 60.0) < 1.0
    assert curve.r_squared > 0.99


def test_half_life_estimator_on_synthetic() -> None:
    snaps = _decaying_history()
    estimate = HalfLifeEstimator().estimate(snaps)
    assert estimate.sample_timestamps == 5
    assert estimate.decaying
    assert estimate.half_life_days is not None
    assert estimate.half_life_days > 0
    assert 0.0 <= estimate.confidence <= 1.0
    assert estimate.usefulness_trend in {
        "losing_differentiation",
        "declining_usefulness",
        "approaching_saturation",
        "mixed",
        "stable",
    }


def test_cohort_series_two_model_gap() -> None:
    t0 = datetime(2025, 6, 1, tzinfo=UTC)
    snaps = [
        _snap(eid="e1", agent="a", score=0.4, ts=t0),
        _snap(eid="e1", agent="b", score=0.7, ts=t0),
    ]
    _ts, diffs, sats, counts = cohort_series(snaps)
    assert diffs == [pytest.approx(0.3)]
    assert sats == [pytest.approx(0.55)]
    assert counts == [2]


def test_trend_analyzer_series() -> None:
    snaps = _decaying_history()
    report = TrendAnalyzer().analyze(snaps)
    assert len(report.score_vs_time) == 10
    assert "local" in report.provider_trends
    assert "hosted" in report.provider_trends
    assert len(report.differentiation_vs_time) == 5
    assert report.metadata["n_cohorts"] == 5


def test_regression_detector_flags_drop() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    # Flat gap, then collapse (large absolute drop; z-score relaxed for short series)
    gaps = [0.30, 0.30, 0.30, 0.02]
    snaps: list[BenchmarkSnapshot] = []
    for i, gap in enumerate(gaps):
        ts = t0 + timedelta(days=14 * i)
        eid = f"exp_reg_{i}"
        snaps.append(_snap(eid=eid, agent="a", score=0.5 - gap / 2, ts=ts))
        snaps.append(_snap(eid=eid, agent="b", score=0.5 + gap / 2, ts=ts))
    events = RegressionDetector(z_threshold=1.0, min_abs_diff_drop=0.1).detect(snaps)
    kinds = {e.kind for e in events}
    assert "differentiation_drop" in kinds


def test_exporter_writes_artifacts(tmp_path: Path) -> None:
    hist_dir = tmp_path / "history"
    out_dir = tmp_path / "report"
    hist = BenchmarkHistory(history_dir=hist_dir)
    hist.replace_all(_decaying_history())
    exporter = ObservatoryExporter(history_dir=hist_dir)
    path = exporter.export(out_dir, formats={"json", "markdown", "html"}, write_png=False)
    assert (path / "benchmark_decay.json").is_file()
    assert (path / "benchmark_trends.json").is_file()
    assert (path / "benchmark_half_life.md").is_file()
    assert (path / "charts" / "differentiation_curve.html").is_file()
    decay = json.loads((path / "benchmark_decay.json").read_text(encoding="utf-8"))
    assert "half_life_days" in decay
    assert "lambda_per_day" in decay


def test_insufficient_history_low_confidence() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    snaps = [
        _snap(eid="e1", agent="a", score=0.5, ts=t0),
        _snap(eid="e1", agent="b", score=0.6, ts=t0),
    ]
    estimate = HalfLifeEstimator().estimate(snaps)
    assert estimate.sample_timestamps == 1
    assert estimate.confidence < 0.5
    assert any("≥3" in n or "Only 1" in n for n in estimate.notes)


def test_cli_observatory_help() -> None:
    result = runner.invoke(cli_app, ["observatory", "--help"])
    assert result.exit_code == 0
    assert "ingest" in result.stdout
    assert "analyze" in result.stdout
    assert "trend" in result.stdout
    assert "report" in result.stdout
    assert "export" in result.stdout


def test_cli_observatory_analyze_from_history(tmp_path: Path) -> None:
    hist_dir = tmp_path / "obs"
    BenchmarkHistory(history_dir=hist_dir).replace_all(_decaying_history())
    out = tmp_path / "out"
    result = runner.invoke(
        cli_app,
        [
            "observatory",
            "analyze",
            "--history-dir",
            str(hist_dir),
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (out / "benchmark_decay.json").is_file()
    assert "half_life=" in result.stdout
