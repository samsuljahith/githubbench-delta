"""Contextvars for current run/trace (future OpenTelemetry bridge)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass

from githubbench_delta.observability.ids import new_run_id, new_span_id, new_trace_id


@dataclass(slots=True)
class ObservabilityContext:
    """Active observability identifiers for the current async task."""

    run_id: str
    trace_id: str
    parent_trace_id: str | None = None
    span_id: str | None = None
    agent_id: str | None = None
    task_id: str | None = None


_current: ContextVar[ObservabilityContext | None] = ContextVar(
    "githubbench_observability",
    default=None,
)


def get_context() -> ObservabilityContext | None:
    """Return the current observability context, if any."""

    return _current.get()


def require_context() -> ObservabilityContext:
    """Return the current context or raise if unbound."""

    ctx = _current.get()
    if ctx is None:
        raise RuntimeError("Observability context is not set")
    return ctx


@contextmanager
def bind_context(
    *,
    run_id: str | None = None,
    trace_id: str | None = None,
    parent_trace_id: str | None = None,
    agent_id: str | None = None,
    task_id: str | None = None,
) -> Iterator[ObservabilityContext]:
    """Bind a new observability context for the duration of the block."""

    ctx = ObservabilityContext(
        run_id=run_id or new_run_id(),
        trace_id=trace_id or new_trace_id(),
        parent_trace_id=parent_trace_id,
        span_id=new_span_id(),
        agent_id=agent_id,
        task_id=task_id,
    )
    token: Token[ObservabilityContext | None] = _current.set(ctx)
    try:
        yield ctx
    finally:
        _current.reset(token)


@contextmanager
def child_span(parent: ObservabilityContext | None = None) -> Iterator[ObservabilityContext]:
    """Open a child span under the current (or provided) parent context."""

    parent_ctx = parent or require_context()
    child = ObservabilityContext(
        run_id=parent_ctx.run_id,
        trace_id=new_trace_id(),
        parent_trace_id=parent_ctx.trace_id,
        span_id=new_span_id(),
        agent_id=parent_ctx.agent_id,
        task_id=parent_ctx.task_id,
    )
    token = _current.set(child)
    try:
        yield child
    finally:
        _current.reset(token)
