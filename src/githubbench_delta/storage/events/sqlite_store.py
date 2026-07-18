"""SQLite event store backend."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock

from githubbench_delta.storage.events.base import EventStore
from githubbench_delta.trajectory.events import ExecutionEvent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS execution_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    parent_trace_id TEXT,
    timestamp TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_run_id ON execution_events(run_id);
CREATE INDEX IF NOT EXISTS idx_events_task_id ON execution_events(task_id);
CREATE INDEX IF NOT EXISTS idx_events_agent_id ON execution_events(agent_id);
"""


class SQLiteEventStore(EventStore):
    """Persist execution events in SQLite (OLTP)."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def append(self, event: ExecutionEvent) -> None:
        self.append_many([event])

    def append_many(self, events: list[ExecutionEvent]) -> None:
        if not events:
            return
        rows = [
            (
                e.event_id,
                e.run_id,
                e.trace_id,
                e.parent_trace_id,
                e.timestamp.isoformat(),
                str(e.agent_id),
                e.task_id,
                e.stage.value,
                e.model_dump_json(),
            )
            for e in events
        ]
        with self._lock:
            self._conn.executemany(
                """
                INSERT OR REPLACE INTO execution_events (
                    event_id, run_id, trace_id, parent_trace_id, timestamp,
                    agent_id, task_id, stage, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            self._conn.commit()

    def query(
        self,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        limit: int | None = None,
    ) -> list[ExecutionEvent]:
        clauses: list[str] = []
        params: list[object] = []
        if run_id is not None:
            clauses.append("run_id = ?")
            params.append(run_id)
        if task_id is not None:
            clauses.append("task_id = ?")
            params.append(task_id)
        if agent_id is not None:
            clauses.append("agent_id = ?")
            params.append(agent_id)
        sql = "SELECT payload FROM execution_events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY timestamp ASC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
        return [ExecutionEvent.model_validate(json.loads(row[0])) for row in rows]

    def flush(self) -> None:
        with self._lock:
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
