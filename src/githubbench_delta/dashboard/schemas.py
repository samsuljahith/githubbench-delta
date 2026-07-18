"""Pydantic schemas for the dashboard API."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Paginated response envelope."""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 50
    sort: str | None = None
    order: str = "desc"


class Principal(BaseModel):
    """Authenticated principal stub (anonymous until auth lands)."""

    subject: str = "anonymous"
    roles: list[str] = Field(default_factory=lambda: ["viewer"])
    authenticated: bool = False


class ExperimentSummary(BaseModel):
    experiment_id: str
    name: str = ""
    status: str = ""
    seed: int = 42
    trial_count: int = 1
    agent_ids: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    dataset_path: str = ""
    created_at: str | None = None
    updated_at: str | None = None
    units_done: int = 0
    units_total: int = 0
    mean_overall_score: float | None = None


class ExperimentDetail(BaseModel):
    experiment: dict[str, Any]
    run: dict[str, Any] | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)


class EvaluationRow(BaseModel):
    experiment_id: str
    run_id: str = ""
    unit_key: str
    task_id: str
    agent_id: str
    trial_index: int = 0
    overall_score: float | None = None
    confidence_score: float | None = None
    group_scores: dict[str, float] = Field(default_factory=dict)
    success: bool | None = None
    category: str | None = None
    metric_scores: dict[str, float] = Field(default_factory=dict)
    latency_ms: float | None = None
    cost_usd: float | None = None


class LeaderboardRow(BaseModel):
    agent_id: str
    overall_score: float = 0.0
    group_scores: dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    success_rate: float = 0.0
    n_trials: int = 0


class TaskRow(BaseModel):
    task_id: str
    category: str | None = None
    difficulty: str | None = None
    language: str | None = None
    repository: str | None = None
    mean_score: float | None = None
    n_evals: int = 0
    agents: list[str] = Field(default_factory=list)


class MetricStat(BaseModel):
    metric_id: str
    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    max: float = 0.0
    n: int = 0
    importance: float = 0.0
    histogram: list[int] = Field(default_factory=list)
    histogram_bins: list[float] = Field(default_factory=list)


class TrajectoryIndexItem(BaseModel):
    unit_key: str
    task_id: str
    agent_id: str
    trial_index: int = 0
    success: bool | None = None
    step_count: int = 0


class TrajectoryDetail(BaseModel):
    unit_key: str
    task_id: str
    agent_id: str
    trial_index: int = 0
    success: bool | None = None
    final_output: str = ""
    error: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    retries: int = 0
    plan: str = ""


class SettingsSnapshot(BaseModel):
    results_dir: str
    sqlite_path: str
    dataset_default: str = "datasets/v1"
    version: str = ""
    auth_enabled: bool = False
    websocket_enabled: bool = False
    notes: str = "Read-only dashboard settings; authentication not enabled."


class AgentCompareResponse(BaseModel):
    agents: list[str]
    group_scores: dict[str, dict[str, float]] = Field(default_factory=dict)
    metric_means: dict[str, dict[str, float]] = Field(default_factory=dict)
    leaderboard: list[LeaderboardRow] = Field(default_factory=list)


class CorrelationResponse(BaseModel):
    metrics: list[str]
    matrix: list[list[float]]


class OverviewResponse(BaseModel):
    experiment_count: int = 0
    evaluation_count: int = 0
    agent_ids: list[str] = Field(default_factory=list)
    latest_experiments: list[ExperimentSummary] = Field(default_factory=list)
    mean_overall_score: float | None = None
