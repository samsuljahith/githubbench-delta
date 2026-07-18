"""Structured execution events for trajectory capture."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from githubbench_delta.core.models import AgentId
from githubbench_delta.observability.ids import new_event_id, new_trace_id


class LifecycleStage(StrEnum):
    """Agent lifecycle and runtime event stages."""

    INITIALIZE = "initialize"
    PREPARE_TASK = "prepare_task"
    PLAN = "plan"
    EXECUTE = "execute"
    VALIDATE = "validate"
    CLEANUP = "cleanup"
    TOOL = "tool"
    PROVIDER = "provider"


class ExecutionEvent(BaseModel):
    """One structured event in an agent execution trajectory."""

    event_id: str = Field(default_factory=new_event_id)
    trace_id: str = Field(default_factory=new_trace_id)
    parent_trace_id: str | None = None
    run_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    agent_id: AgentId | str
    task_id: str
    stage: LifecycleStage
    tool: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    error: str | None = None
    warning: str | None = None
    level: str = "info"
    metadata: dict[str, Any] = Field(default_factory=dict)
