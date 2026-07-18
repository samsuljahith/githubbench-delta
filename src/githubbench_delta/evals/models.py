"""Evaluation-run models used by the evals package."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from githubbench_delta.core.models import AgentId, EvaluationResult, RunSummary


class EvalRunRequest(BaseModel):
    """Request to start an evaluation run (API/CLI)."""

    agent_ids: list[AgentId] = Field(default_factory=list)
    task_ids: list[str] = Field(default_factory=list)
    seed: int | None = None
    trial_count: int | None = None


class EvalRunStatus(BaseModel):
    """Status snapshot for an in-progress or completed evaluation run."""

    run_id: str
    status: str
    created_at: datetime | None = None
    completed_at: datetime | None = None
    summary: RunSummary | None = None
    evaluations: list[EvaluationResult] = Field(default_factory=list)
