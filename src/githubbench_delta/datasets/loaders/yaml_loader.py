"""YAML dataset loader (list of tasks or {tasks: [...]})."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from githubbench_delta.core.errors import DatasetValidationError
from githubbench_delta.datasets.base import BaseDatasetLoader
from githubbench_delta.datasets.loaders._common import extract_task_id, record_to_task
from githubbench_delta.datasets.loaders.json_loader import _unwrap
from githubbench_delta.tasks.base import BaseTask


class YAMLDatasetLoader(BaseDatasetLoader):
    """Load tasks from a ``.yaml`` / ``.yml`` file."""

    def load(self, path: Path) -> list[BaseTask]:
        path = Path(path)
        if not path.is_file():
            raise DatasetValidationError(f"YAML dataset not found: {path}")
        with path.open(encoding="utf-8") as handle:
            data: Any = yaml.safe_load(handle)
        return [record_to_task(item) for item in _unwrap(data)]

    def list_task_ids(self, path: Path) -> list[str]:
        path = Path(path)
        with path.open(encoding="utf-8") as handle:
            data: Any = yaml.safe_load(handle)
        return [extract_task_id(item) for item in _unwrap(data)]
