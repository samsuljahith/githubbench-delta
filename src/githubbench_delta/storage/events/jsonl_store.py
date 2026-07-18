"""JSONL event store backend."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from githubbench_delta.storage.events.base import EventStore
from githubbench_delta.trajectory.events import ExecutionEvent


class JSONLEventStore(EventStore):
    """Append events as one JSON object per line."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append(self, event: ExecutionEvent) -> None:
        line = event.model_dump_json() + "\n"
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def append_many(self, events: list[ExecutionEvent]) -> None:
        if not events:
            return
        payload = "".join(e.model_dump_json() + "\n" for e in events)
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(payload)

    def query(
        self,
        *,
        run_id: str | None = None,
        task_id: str | None = None,
        agent_id: str | None = None,
        limit: int | None = None,
    ) -> list[ExecutionEvent]:
        if not self.path.is_file():
            return []
        results: list[ExecutionEvent] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                event = ExecutionEvent.model_validate(json.loads(line))
                if run_id is not None and event.run_id != run_id:
                    continue
                if task_id is not None and event.task_id != task_id:
                    continue
                if agent_id is not None and str(event.agent_id) != agent_id:
                    continue
                results.append(event)
                if limit is not None and len(results) >= limit:
                    break
        return results
