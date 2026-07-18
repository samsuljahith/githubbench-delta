"""ID generators for runs, traces, and events (OTEL-compatible field names)."""

from __future__ import annotations

import uuid


def new_run_id() -> str:
    """Generate a unique evaluation/agent run identifier."""

    return f"run_{uuid.uuid4().hex}"


def new_trace_id() -> str:
    """Generate a 32-char hex trace id (OpenTelemetry-compatible length)."""

    return uuid.uuid4().hex


def new_span_id() -> str:
    """Generate a 16-char hex span/parent id (OpenTelemetry-compatible length)."""

    return uuid.uuid4().hex[:16]


def new_event_id() -> str:
    """Generate a unique event identifier."""

    return f"evt_{uuid.uuid4().hex}"
