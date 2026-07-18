"""Experiment / run manifests and work-unit models for Phase 5."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from githubbench_delta.core.models import AgentId


class ExperimentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class WorkUnit(BaseModel):
    """One (task, agent, trial) execution unit."""

    task_id: str
    agent_id: AgentId | str
    trial_index: int = 0

    def key(self) -> str:
        return f"{self.task_id}::{self.agent_id}::{self.trial_index}"


class ExperimentSpec(BaseModel):
    """Inputs describing an experiment to run."""

    dataset_path: Path | str
    agent_ids: list[str] = Field(default_factory=list)
    task_ids: list[str] | None = None
    trial_count: int = 1
    seed: int = 42
    max_concurrency: int = 1
    resume: bool = True
    use_cache: bool = True
    dry_run: bool = False
    name: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentManifest(BaseModel):
    """Persisted experiment.json contents."""

    experiment_id: str
    name: str = ""
    status: ExperimentStatus = ExperimentStatus.PENDING
    seed: int = 42
    trial_count: int = 1
    agent_ids: list[str] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    dataset_path: str = ""
    max_concurrency: int = 1
    resume: bool = True
    use_cache: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class UnitError(BaseModel):
    unit_key: str
    error: str
    timestamp: datetime | None = None


class RunManifest(BaseModel):
    """Persisted run.json contents."""

    run_id: str
    experiment_id: str
    status: RunStatus = RunStatus.PENDING
    units_total: int = 0
    units_done: int = 0
    units_failed: int = 0
    completed_units: list[str] = Field(default_factory=list)
    failed_units: list[UnitError] = Field(default_factory=list)
    current_unit: str | None = None
    seed: int = 42
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ProgressEvent(BaseModel):
    """Progress reporting payload for ExperimentRunner."""

    units_done: int
    units_total: int
    current_unit: str | None = None
    status: str = "running"
    message: str = ""


class CachedEvaluation(BaseModel):
    """Cached agent + evaluation payload."""

    cache_key: str
    agent_result: dict[str, Any]
    evaluation_result: dict[str, Any]
