"""Persistent JSONL history of benchmark snapshots."""

from __future__ import annotations

import json
from pathlib import Path

from githubbench_delta.observatory.models import BenchmarkSnapshot

DEFAULT_HISTORY_DIR = Path("results/observatory")
HISTORY_FILENAME = "history.jsonl"
INDEX_FILENAME = "index.json"


class BenchmarkHistory:
    """Append-only (idempotent) store of :class:`BenchmarkSnapshot` records."""

    def __init__(self, history_dir: Path | str | None = None) -> None:
        self.history_dir = Path(history_dir or DEFAULT_HISTORY_DIR)
        self.history_path = self.history_dir / HISTORY_FILENAME
        self.index_path = self.history_dir / INDEX_FILENAME
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[BenchmarkSnapshot]:
        if not self.history_path.is_file():
            return []
        snapshots: list[BenchmarkSnapshot] = []
        for line in self.history_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            snapshots.append(BenchmarkSnapshot.model_validate_json(line))
        snapshots.sort(key=lambda s: (s.timestamp, s.agent_id, s.experiment_id))
        return snapshots

    def append(self, snapshot: BenchmarkSnapshot) -> bool:
        """Append snapshot if key is new. Returns True if written."""

        existing = {s.history_key: s for s in self.load()}
        if snapshot.history_key in existing:
            return False
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(snapshot.model_dump_json() + "\n")
        self._rewrite_index([*existing.values(), snapshot])
        return True

    def extend(self, snapshots: list[BenchmarkSnapshot]) -> int:
        written = 0
        for snap in snapshots:
            if self.append(snap):
                written += 1
        return written

    def replace_all(self, snapshots: list[BenchmarkSnapshot]) -> None:
        """Overwrite history (used for tests / demo seeds)."""

        self.history_dir.mkdir(parents=True, exist_ok=True)
        lines = [s.model_dump_json() for s in sorted(snapshots, key=lambda x: x.timestamp)]
        self.history_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        self._rewrite_index(snapshots)

    def _rewrite_index(self, snapshots: list[BenchmarkSnapshot]) -> None:
        by_key = {s.history_key: s for s in snapshots}
        unique = list(by_key.values())
        unique.sort(key=lambda s: (s.timestamp, s.agent_id))
        payload = {
            "count": len(unique),
            "experiments": sorted({s.experiment_id for s in unique}),
            "agents": sorted({s.agent_id for s in unique}),
            "providers": sorted({s.provider for s in unique}),
            "models": sorted({s.model for s in unique}),
            "t_min": min((s.timestamp.isoformat() for s in unique), default=None),
            "t_max": max((s.timestamp.isoformat() for s in unique), default=None),
        }
        self.index_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def summary(self) -> dict[str, object]:
        if self.index_path.is_file():
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        snaps = self.load()
        self._rewrite_index(snaps)
        return json.loads(self.index_path.read_text(encoding="utf-8"))
