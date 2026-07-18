"""Event store abstraction (persistence only, no business logic)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from githubbench_delta.trajectory.events import ExecutionEvent


class EventStore(ABC):
    """Append-only persistence for execution events."""

    @abstractmethod
    def append(self, event: ExecutionEvent) -> None:
        """Persist a single event."""

    @abstractmethod
    def append_many(self, events: list[ExecutionEvent]) -> None:
        """Persist multiple events."""

    @abstractmethod
    def query(
        self,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        limit: int | None = None,
    ) -> list[ExecutionEvent]:
        """Query stored events with optional filters."""

    def flush(self) -> None:
        """Flush buffered writes (default no-op)."""

        return None

    def close(self) -> None:
        """Release resources (default no-op)."""

        return None

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
