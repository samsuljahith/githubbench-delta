"""Create and update run.json manifests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from githubbench_delta.observability.ids import new_run_id
from githubbench_delta.pipeline.models import RunManifest, RunStatus, UnitError, WorkUnit
from githubbench_delta.storage.results.sqlite_store import SQLiteResultStore


class RunManager:
    """Manage per-experiment run.json lifecycle and progress."""

    def __init__(
        self,
        experiment_dir: Path | str,
        *,
        sqlite_store: SQLiteResultStore | None = None,
    ) -> None:
        self.experiment_dir = Path(experiment_dir)
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.experiment_dir / "run.json"
        self._sqlite = sqlite_store

    def create(
        self,
        *,
        experiment_id: str,
        units_total: int,
        seed: int,
        run_id: str | None = None,
    ) -> RunManifest:
        now = datetime.now(UTC)
        manifest = RunManifest(
            run_id=run_id or new_run_id(),
            experiment_id=experiment_id,
            status=RunStatus.PENDING,
            units_total=units_total,
            seed=seed,
            created_at=now,
            updated_at=now,
        )
        self.save(manifest)
        return manifest

    def save(self, manifest: RunManifest) -> Path:
        manifest.updated_at = datetime.now(UTC)
        self.path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if self._sqlite is not None:
            self._sqlite.save_run_payload(
                manifest.run_id,
                manifest.experiment_id,
                manifest.model_dump(mode="json"),
            )
        return self.path

    def load(self) -> RunManifest:
        return RunManifest.model_validate(json.loads(self.path.read_text(encoding="utf-8")))

    def mark_running(self, manifest: RunManifest) -> RunManifest:
        manifest.status = RunStatus.RUNNING
        self.save(manifest)
        return manifest

    def mark_unit_progress(
        self,
        manifest: RunManifest,
        unit: WorkUnit,
        *,
        success: bool,
        error: str | None = None,
    ) -> RunManifest:
        key = unit.key()
        manifest.current_unit = key
        if success:
            if key not in manifest.completed_units:
                manifest.completed_units.append(key)
                manifest.units_done = len(manifest.completed_units)
        else:
            manifest.units_failed += 1
            manifest.failed_units.append(
                UnitError(unit_key=key, error=error or "unknown", timestamp=datetime.now(UTC))
            )
        self.save(manifest)
        return manifest

    def finalize(
        self,
        manifest: RunManifest,
        *,
        interrupted: bool = False,
        error: str | None = None,
    ) -> RunManifest:
        if interrupted:
            manifest.status = RunStatus.INTERRUPTED
        elif manifest.units_failed and manifest.units_done == 0:
            manifest.status = RunStatus.FAILED
        else:
            manifest.status = RunStatus.COMPLETED
        manifest.error = error
        manifest.current_unit = None
        self.save(manifest)
        return manifest
