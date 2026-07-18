"""JSON dataset loader (list of task objects or {tasks: [...]})."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from githubbench_delta.core.errors import DatasetValidationError
from githubbench_delta.datasets.base import BaseDatasetLoader
from githubbench_delta.datasets.loaders._common import extract_task_id, record_to_task
from githubbench_delta.tasks.base import BaseTask


def _unwrap(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and "tasks" in data:
        records = data["tasks"]
    else:
        raise DatasetValidationError(
            "JSON dataset must be a list of tasks or an object with a 'tasks' array"
        )
    if not isinstance(records, list):
        raise DatasetValidationError("'tasks' must be a list")
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(records):
        if not isinstance(item, dict):
            raise DatasetValidationError(f"Task at index {idx} must be an object")
        out.append(item)
    return out


class JSONDatasetLoader(BaseDatasetLoader):
    """Load tasks from a ``.json`` file."""

    def load(self, path: Path) -> list[BaseTask]:
        path = Path(path)
        if not path.is_file():
            raise DatasetValidationError(f"JSON dataset not found: {path}")
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return [record_to_task(item) for item in _unwrap(data)]

    def list_task_ids(self, path: Path) -> list[str]:
        path = Path(path)
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return [extract_task_id(item) for item in _unwrap(data)]
