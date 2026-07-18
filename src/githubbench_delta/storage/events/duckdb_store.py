"""DuckDB event store stub (analytics OLAP — Phase 5+)."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.storage.events.base import EventStore
from githubbench_delta.trajectory.events import ExecutionEvent


class DuckDBEventStore(EventStore):
    """DuckDB-backed event store interface.

    TODO(phase-5): Implement append/query against DuckDB for analytics.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def append(self, event: ExecutionEvent) -> None:
        raise NotImplementedError("DuckDBEventStore.append will be implemented later")

    def append_many(self, events: list[ExecutionEvent]) -> None:
        raise NotImplementedError("DuckDBEventStore.append_many will be implemented later")

    def query(
        self,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        limit: int | None = None,
    ) -> list[ExecutionEvent]:
        raise NotImplementedError("DuckDBEventStore.query will be implemented later")
