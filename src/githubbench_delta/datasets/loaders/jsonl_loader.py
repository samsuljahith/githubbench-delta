"""JSONL dataset loader (one task object per line)."""

from __future__ import annotations

import json
from pathlib import Path

from githubbench_delta.core.errors import DatasetValidationError
from githubbench_delta.datasets.base import BaseDatasetLoader
from githubbench_delta.datasets.loaders._common import extract_task_id, record_to_task
from githubbench_delta.tasks.base import BaseTask


class JSONLDatasetLoader(BaseDatasetLoader):
    """Load tasks from a ``.jsonl`` file."""

    def load(self, path: Path) -> list[BaseTask]:
        path = Path(path)
        if not path.is_file():
            raise DatasetValidationError(f"JSONL dataset not found: {path}")
        tasks: list[BaseTask] = []
        with path.open(encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise DatasetValidationError(
                        f"Invalid JSON on line {lineno} of {path}: {exc}"
                    ) from exc
                if not isinstance(data, dict):
                    raise DatasetValidationError(f"Line {lineno} of {path} must be a JSON object")
                tasks.append(record_to_task(data))
        return tasks

    def list_task_ids(self, path: Path) -> list[str]:
        path = Path(path)
        ids: list[str] = []
        with path.open(encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise DatasetValidationError(
                        f"Invalid JSON on line {lineno} of {path}: {exc}"
                    ) from exc
                if not isinstance(data, dict):
                    raise DatasetValidationError(f"Line {lineno} of {path} must be a JSON object")
                ids.append(extract_task_id(data))
        return ids
