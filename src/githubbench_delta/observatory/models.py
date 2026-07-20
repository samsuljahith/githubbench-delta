"""Pydantic models for the Half-Life Observatory."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class MetricSummary(BaseModel):
    """Aggregated metric / group scores for a snapshot."""

    group_scores: dict[str, float] = Field(default_factory=dict)
    metric_means: dict[str, float] = Field(default_factory=dict)
    confidence: float | None = None


class BenchmarkSnapshot(BaseModel):
    """One historical observation of an agent on a benchmark run."""

    snapshot_id: str
    timestamp: datetime
    benchmark_version: str
    experiment_id: str
    agent_id: str
    model: str
    provider: str
    score: float
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    tool_usage: float = 0.0
    task_count: int = 0
    success_rate: float = 0.0
    metric_summary: MetricSummary = Field(default_factory=MetricSummary)
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def history_key(self) -> str:
        return f"{self.experiment_id}::{self.agent_id}"


class DecayCurvePoint(BaseModel):
    """Single point on an estimated or observed decay curve."""

    t_days: float
    differentiation: float
    fitted: float | None = None
    saturation: float | None = None
    timestamp: datetime | None = None


class DecayCurve(BaseModel):
    """Fitted exponential decay of differentiation over time."""

    lambda_per_day: float
    d0: float
    r_squared: float
    points: list[DecayCurvePoint] = Field(default_factory=list)
    formula: str = "D(t) = D0 * exp(-lambda * t)"


class HalfLifeEstimate(BaseModel):
    """Benchmark half-life estimate with supporting series."""

    half_life_days: float | None
    confidence: float
    decaying: bool
    decay_curve: DecayCurve
    saturation_series: list[DecayCurvePoint] = Field(default_factory=list)
    usefulness_trend: str
    differentiation_series: list[DecayCurvePoint] = Field(default_factory=list)
    sample_timestamps: int = 0
    sample_models: int = 0
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrendSeriesPoint(BaseModel):
    timestamp: datetime
    value: float
    label: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrendReport(BaseModel):
    """Multi-series trend analysis over history."""

    score_vs_time: list[TrendSeriesPoint] = Field(default_factory=list)
    provider_trends: dict[str, list[TrendSeriesPoint]] = Field(default_factory=dict)
    model_progression: dict[str, list[TrendSeriesPoint]] = Field(default_factory=dict)
    saturation_vs_time: list[TrendSeriesPoint] = Field(default_factory=list)
    differentiation_vs_time: list[TrendSeriesPoint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RegressionEvent(BaseModel):
    """Detected sudden change in differentiation or saturation."""

    timestamp: datetime
    kind: str
    severity: float
    message: str
    before: float
    after: float
    metadata: dict[str, Any] = Field(default_factory=dict)
