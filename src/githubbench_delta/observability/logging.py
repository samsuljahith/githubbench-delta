"""Structured JSON logging helpers."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from githubbench_delta.observability.context import get_context

_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


class StructuredFormatter(logging.Formatter):
    """Emit one JSON object per log record, enriched with trace fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        ctx = get_context()
        if ctx is not None:
            payload["run_id"] = ctx.run_id
            payload["trace_id"] = ctx.trace_id
            if ctx.parent_trace_id:
                payload["parent_trace_id"] = ctx.parent_trace_id
            if ctx.span_id:
                payload["span_id"] = ctx.span_id
            if ctx.agent_id:
                payload["agent_id"] = ctx.agent_id
            if ctx.task_id:
                payload["task_id"] = ctx.task_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("event_id", "stage", "tool", "latency_ms", "cost_usd"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def get_logger(name: str = "githubbench_delta") -> logging.Logger:
    """Return a module logger (caller configures handlers as needed)."""

    return logging.getLogger(name)


def parse_log_level(level: str | int) -> int:
    """Parse a log level name or int."""

    if isinstance(level, int):
        return level
    key = level.strip().lower()
    if key not in _LEVELS:
        raise ValueError(f"Unknown log level {level!r}; use {', '.join(_LEVELS)}")
    return _LEVELS[key]


def configure_structured_logging(
    *,
    level: int = logging.INFO,
    stream: Any = None,
) -> logging.Logger:
    """Configure the root githubbench logger with a JSON formatter."""

    logger = get_logger()
    logger.handlers.clear()
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def configure_cli_logging(
    *,
    level: str | int = "info",
    structured: bool = True,
    stream: Any = None,
) -> logging.Logger:
    """Configure logging for CLI entrypoints (stderr; optional JSON)."""

    resolved = parse_log_level(level)
    if structured:
        return configure_structured_logging(level=resolved, stream=stream)
    logger = get_logger()
    logger.handlers.clear()
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(resolved)
    logger.propagate = False
    return logger
