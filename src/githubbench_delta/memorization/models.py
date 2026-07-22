"""Pydantic models for Memorization Discounted Scoring (MDS)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

GENERATOR_VERSION = "1.0.0"
AnalysisMode = Literal["twin", "proxy"]


def utc_now() -> datetime:
    return datetime.now(UTC)


class TwinTaskSpec(BaseModel):
    """Sidecar twin task record (SerializedTaskRecord-compatible extras)."""

    id: str
    parent_task_id: str
    twin_kind: str = "paraphrase"
    generator_version: str = GENERATOR_VERSION
    record: dict[str, Any] = Field(default_factory=dict)


class TwinPair(BaseModel):
    """Parent ↔ twin linkage with optional scores."""

    parent_task_id: str
    twin_task_id: str
    agent_id: str
    s_obs: float = Field(ge=0.0, le=1.0)
    s_twin: float | None = Field(default=None, ge=0.0, le=1.0)
    lift: float = Field(ge=0.0, le=1.0)
    generalization: float = Field(ge=0.0, le=1.0)
    mode: AnalysisMode = "proxy"
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorizationLift(BaseModel):
    """Per-agent aggregate memorization lift estimate."""

    agent_id: str
    mean_lift: float = Field(ge=0.0, le=1.0)
    mean_obs: float = Field(ge=0.0, le=1.0)
    mean_generalization: float = Field(ge=0.0, le=1.0)
    n_pairs: int = 0
    mode: AnalysisMode = "proxy"
    pairs: list[TwinPair] = Field(default_factory=list)


class PosteriorInterval(BaseModel):
    """Credible interval for memorization lift (and derived discounted score)."""

    agent_id: str
    mean: float
    lower: float
    upper: float
    level: float = 0.95
    alpha: float = 1.0
    beta: float = 1.0
    discounted_mean: float | None = None
    discounted_lower: float | None = None
    discounted_upper: float | None = None
    mean_obs: float | None = None


class CapabilityBreakdown(BaseModel):
    """G / L decomposition for one agent."""

    agent_id: str
    observed_score: float
    generalization: float
    memorization_lift: float
    discounted_score: float
    residual: float = 0.0
    mode: AnalysisMode = "proxy"
    n_tasks: int = 0
    notes: list[str] = Field(default_factory=list)


class MemorizationReport(BaseModel):
    """Full MDS analysis payload."""

    experiment_ids: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    mode: AnalysisMode = "proxy"
    lifts: list[MemorizationLift] = Field(default_factory=list)
    breakdowns: list[CapabilityBreakdown] = Field(default_factory=list)
    posteriors: list[PosteriorInterval] = Field(default_factory=list)
    twin_specs: list[TwinTaskSpec] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    output_dir: str = ""
    artifacts: list[str] = Field(default_factory=list)
