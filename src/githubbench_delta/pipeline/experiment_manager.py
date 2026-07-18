"""Create and persist experiment manifests."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from githubbench_delta.core.config import AppConfig, load_config
from githubbench_delta.pipeline.models import ExperimentManifest, ExperimentSpec, ExperimentStatus
from githubbench_delta.storage.results.sqlite_store import SQLiteResultStore


def new_experiment_id() -> str:
    return f"exp_{uuid.uuid4().hex[:16]}"


class ExperimentManager:
    """Manage experiment directories and experiment.json manifests."""

    def __init__(
        self,
        *,
        results_dir: Path | str | None = None,
        app_config: AppConfig | None = None,
        sqlite_store: SQLiteResultStore | None = None,
    ) -> None:
        self.app_config = app_config or load_config()
        self.results_dir = Path(results_dir or self.app_config.runtime.pipeline.results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._sqlite = sqlite_store

    def experiment_dir(self, experiment_id: str) -> Path:
        path = self.results_dir / experiment_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create(self, spec: ExperimentSpec, *, task_ids: list[str]) -> ExperimentManifest:
        """Create a new experiment and write experiment.json."""

        now = datetime.now(UTC)
        manifest = ExperimentManifest(
            experiment_id=new_experiment_id(),
            name=spec.name or f"experiment-{now.strftime('%Y%m%d-%H%M%S')}",
            status=ExperimentStatus.PENDING,
            seed=spec.seed,
            trial_count=spec.trial_count,
            agent_ids=list(spec.agent_ids),
            task_ids=list(task_ids),
            dataset_path=str(spec.dataset_path),
            max_concurrency=spec.max_concurrency,
            resume=spec.resume,
            use_cache=spec.use_cache,
            created_at=now,
            updated_at=now,
            config_snapshot={
                "seed": self.app_config.runtime.seed,
                "trial_count": self.app_config.runtime.trial_count,
                "pipeline": self.app_config.runtime.pipeline.model_dump(mode="json"),
            },
            metadata=dict(spec.metadata),
        )
        self.save(manifest)
        return manifest

    def save(self, manifest: ExperimentManifest) -> Path:
        manifest.updated_at = datetime.now(UTC)
        path = self.experiment_dir(manifest.experiment_id) / "experiment.json"
        path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if self._sqlite is not None:
            self._sqlite.save_experiment_payload(
                manifest.experiment_id, manifest.model_dump(mode="json")
            )
        return path

    def load(self, experiment_id: str) -> ExperimentManifest:
        path = self.experiment_dir(experiment_id) / "experiment.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return ExperimentManifest.model_validate(data)

    def list_experiments(self) -> list[ExperimentManifest]:
        out: list[ExperimentManifest] = []
        if not self.results_dir.is_dir():
            return out
        for child in sorted(self.results_dir.iterdir()):
            meta = child / "experiment.json"
            if meta.is_file():
                out.append(
                    ExperimentManifest.model_validate(json.loads(meta.read_text(encoding="utf-8")))
                )
        return out

    def set_status(
        self,
        experiment_id: str,
        status: ExperimentStatus,
        *,
        error: str | None = None,
    ) -> ExperimentManifest:
        manifest = self.load(experiment_id)
        manifest.status = status
        manifest.error = error
        self.save(manifest)
        return manifest
