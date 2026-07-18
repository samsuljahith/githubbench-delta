"""Observability: IDs, context, structured logging (OTEL-ready field names)."""

from githubbench_delta.observability.context import (
    ObservabilityContext,
    bind_context,
    child_span,
    get_context,
    require_context,
)
from githubbench_delta.observability.ids import (
    new_event_id,
    new_run_id,
    new_span_id,
    new_trace_id,
)
from githubbench_delta.observability.logging import (
    configure_cli_logging,
    configure_structured_logging,
    get_logger,
)

__all__ = [
    "ObservabilityContext",
    "bind_context",
    "child_span",
    "get_context",
    "require_context",
    "new_event_id",
    "new_run_id",
    "new_span_id",
    "new_trace_id",
    "configure_cli_logging",
    "configure_structured_logging",
    "get_logger",
]
