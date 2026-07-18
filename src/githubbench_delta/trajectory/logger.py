"""First-class trajectory logger: capture events and project Phase 1 Trajectory."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from githubbench_delta.core.models import (
    AgentId,
    ToolCall,
    ToolResult,
    Trajectory,
    TrajectoryStep,
)
from githubbench_delta.observability.context import get_context
from githubbench_delta.observability.ids import new_event_id, new_trace_id
from githubbench_delta.observability.logging import get_logger
from githubbench_delta.trajectory.events import ExecutionEvent, LifecycleStage

if TYPE_CHECKING:
    from githubbench_delta.storage.events.base import EventStore

logger = get_logger(__name__)


class TrajectoryLogger:
    """Capture every execution event and build a Phase 1 ``Trajectory``."""

    def __init__(
        self,
        *,
        run_id: str,
        agent_id: AgentId | str,
        task_id: str,
        trial_index: int = 0,
        event_store: EventStore | None = None,
    ) -> None:
        self.run_id = run_id
        self.agent_id = agent_id
        self.task_id = task_id
        self.trial_index = trial_index
        self.event_store = event_store
        self.events: list[ExecutionEvent] = []
        self._steps: list[TrajectoryStep] = []
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None
        self._step_index = 0

    def emit(
        self,
        stage: LifecycleStage | str,
        *,
        tool: str | None = None,
        arguments: dict[str, Any] | None = None,
        result: Any = None,
        latency_ms: float | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        cost_usd: float | None = None,
        error: str | None = None,
        warning: str | None = None,
        level: str = "info",
        metadata: dict[str, Any] | None = None,
        parent_trace_id: str | None = None,
        trace_id: str | None = None,
        content: str = "",
    ) -> ExecutionEvent:
        """Append an execution event and optionally persist it."""

        ctx = get_context()
        stage_enum = LifecycleStage(stage) if isinstance(stage, str) else stage
        event = ExecutionEvent(
            event_id=new_event_id(),
            trace_id=trace_id or (ctx.trace_id if ctx else new_trace_id()),
            parent_trace_id=parent_trace_id or (ctx.parent_trace_id if ctx else None),
            run_id=self.run_id,
            agent_id=self.agent_id,
            task_id=self.task_id,
            stage=stage_enum,
            tool=tool,
            arguments=arguments or {},
            result=result,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            error=error,
            warning=warning,
            level="error" if error else level,
            metadata=metadata or {},
        )
        if self.started_at is None:
            self.started_at = event.timestamp
        self.events.append(event)
        self._project_step(event, content=content)
        if self.event_store is not None:
            self.event_store.append(event)
        log_fn = logger.error if error else logger.info
        log_fn(
            "execution_event",
            extra={
                "event_id": event.event_id,
                "stage": event.stage.value,
                "tool": event.tool,
                "latency_ms": event.latency_ms,
                "cost_usd": event.cost_usd,
            },
        )
        return event

    def _project_step(self, event: ExecutionEvent, *, content: str = "") -> None:
        tool_call: ToolCall | None = None
        tool_result: ToolResult | None = None
        kind = event.stage.value
        step_content = content

        if event.stage == LifecycleStage.TOOL and event.tool:
            tool_call = ToolCall(
                id=event.event_id,
                name=event.tool,
                arguments=event.arguments,
                timestamp=event.timestamp,
            )
            success = event.error is None
            tool_result = ToolResult(
                call_id=event.event_id,
                name=event.tool,
                success=success,
                output=str(event.result) if event.result is not None else "",
                error=event.error,
                duration_ms=event.latency_ms,
            )
            kind = "tool"
        elif event.stage == LifecycleStage.PROVIDER:
            kind = "provider"
            if event.result is not None and not step_content:
                step_content = str(event.result)
        elif event.stage == LifecycleStage.PLAN:
            kind = "plan"
            if event.result is not None and not step_content:
                step_content = str(event.result)

        self._steps.append(
            TrajectoryStep(
                index=self._step_index,
                kind=kind,
                content=step_content,
                tool_call=tool_call,
                tool_result=tool_result,
                timestamp=event.timestamp,
                metadata={
                    "event_id": event.event_id,
                    "trace_id": event.trace_id,
                    "parent_trace_id": event.parent_trace_id,
                    "stage": event.stage.value,
                    **event.metadata,
                },
            )
        )
        self._step_index += 1

    def build_trajectory(self) -> Trajectory:
        """Materialize a Phase 1 ``Trajectory`` from captured steps."""

        self.finished_at = datetime.now(UTC)
        agent = self.agent_id if isinstance(self.agent_id, AgentId) else AgentId(str(self.agent_id))
        return Trajectory(
            agent_id=agent,
            task_id=self.task_id,
            trial_index=self.trial_index,
            steps=list(self._steps),
            started_at=self.started_at,
            finished_at=self.finished_at,
            metadata={"run_id": self.run_id, "event_count": len(self.events)},
        )

    def flush(self) -> None:
        """Flush the backing event store if present."""

        if self.event_store is not None:
            self.event_store.flush()
