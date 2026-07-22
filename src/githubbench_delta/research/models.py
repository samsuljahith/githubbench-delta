"""Pydantic models for the research execution platform."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ExperimentStatus = Literal["runnable", "blocked", "pending_data", "completed"]
EvidenceStatus = Literal["present", "absent", "partial"]


def utc_now() -> datetime:
    return datetime.now(UTC)


class ResearchHypothesis(BaseModel):
    statement: str
    null: str = ""
    alternative: str = ""


class ExperimentRequires(BaseModel):
    datasets: list[str] = Field(default_factory=list)
    benchmark_runs: list[str] = Field(default_factory=list)
    human_annotations: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    min_pairs: int = 0
    min_trials: int = 0
    evidence_nodes: list[str] = Field(default_factory=list)


class ResearchExperiment(BaseModel):
    """YAML-driven research experiment definition."""

    id: str
    project: str
    title: str
    hypothesis: ResearchHypothesis
    status: ExperimentStatus = "blocked"
    requires: ExperimentRequires = Field(default_factory=ExperimentRequires)
    evidence_gap_ref: str = ""
    stats_plan: list[str] = Field(default_factory=list)
    artifact_globs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchProject(BaseModel):
    id: str
    title: str
    description: str = ""
    experiments: list[str] = Field(default_factory=list)


class ExperimentManifest(BaseModel):
    """Persisted research experiment artifact manifest."""

    experiment_id: str
    project: str
    title: str
    hypothesis: ResearchHypothesis
    status: ExperimentStatus
    requires: ExperimentRequires
    evidence_gap_ref: str = ""
    git_commit: str | None = None
    config_hash: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    source_artifacts: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReadinessStatus(BaseModel):
    experiment_id: str
    status: ExperimentStatus
    missing_datasets: list[str] = Field(default_factory=list)
    missing_benchmark_runs: list[str] = Field(default_factory=list)
    missing_human_annotations: list[str] = Field(default_factory=list)
    missing_baselines: list[str] = Field(default_factory=list)
    missing_evidence_nodes: list[str] = Field(default_factory=list)
    statistical_ready: bool = False
    publication_ready: bool = False
    notes: list[str] = Field(default_factory=list)


class StatResult(BaseModel):
    """Result of a statistical procedure — never fabricate when ok=False."""

    ok: bool
    method: str
    n: int = 0
    statistic: float | None = None
    p_value: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    effect_size: float | None = None
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PowerEstimate(BaseModel):
    ok: bool
    method: str
    n_required: int | None = None
    mde: float | None = None
    variance: float | None = None
    alpha: float = 0.05
    power: float = 0.8
    notes: list[str] = Field(default_factory=list)


class EvidenceNode(BaseModel):
    id: str
    title: str
    status: EvidenceStatus = "absent"
    description: str = ""
    unlocks: list[str] = Field(default_factory=list)
