"""Dataset manifest generation."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from githubbench_delta.datasets.metadata import DatasetMetadata
from githubbench_delta.tasks.base import BaseTask


class DatasetManifest(BaseModel):
    """Summary document written beside a dataset corpus."""

    dataset_version: str
    task_count: int
    category_counts: dict[str, int] = Field(default_factory=dict)
    language_counts: dict[str, int] = Field(default_factory=dict)
    repositories: list[str] = Field(default_factory=list)
    content_hash: str
    created_at: datetime
    author: str = ""
    description: str = ""
    license: str = "Apache-2.0"
    name: str = ""


def _canonical_task_bytes(tasks: list[BaseTask]) -> bytes:
    payload = [t.model_dump(mode="json") for t in sorted(tasks, key=lambda x: x.id)]
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_content_hash(tasks: list[BaseTask]) -> str:
    """Stable sha256 over canonical task JSON."""

    return hashlib.sha256(_canonical_task_bytes(tasks)).hexdigest()


def generate_manifest(
    tasks: list[BaseTask],
    *,
    metadata: DatasetMetadata | None = None,
) -> DatasetManifest:
    """Build a ``DatasetManifest`` from tasks and optional metadata."""

    category_counts = dict(Counter(t.category.value for t in tasks))
    language_counts = dict(Counter((t.language or "unknown") for t in tasks))
    repos: set[str] = set()
    for task in tasks:
        if task.repository and task.repository.url:
            repos.add(task.repository.url)
        elif task.input.repository_url:
            repos.add(task.input.repository_url)
        elif task.repository and task.repository.local_path:
            repos.add(task.repository.local_path)

    version = (
        metadata.dataset_version if metadata else (tasks[0].dataset_version if tasks else "v1")
    )
    return DatasetManifest(
        name=metadata.name if metadata else "",
        dataset_version=version,
        task_count=len(tasks),
        category_counts=category_counts,
        language_counts=language_counts,
        repositories=sorted(repos),
        content_hash=compute_content_hash(tasks),
        created_at=datetime.now(UTC),
        author=metadata.author if metadata else "",
        description=metadata.description if metadata else "",
        license=metadata.license if metadata else "Apache-2.0",
    )


def write_manifest(manifest: DatasetManifest, path: Path | str) -> Path:
    """Write ``manifest.json`` to ``path`` and return the path."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_dataset_metadata(path: Path | str) -> DatasetMetadata:
    """Load ``dataset.yaml`` / ``dataset.yml`` / ``dataset.json`` metadata."""

    import yaml

    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    data = json.loads(text) if path.suffix.lower() == ".json" else (yaml.safe_load(text) or {})
    return DatasetMetadata.model_validate(data)
