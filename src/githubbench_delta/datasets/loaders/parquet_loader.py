"""Parquet dataset loader stub."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.datasets.base import BaseDatasetLoader
from githubbench_delta.tasks.base import BaseTask


class ParquetDatasetLoader(BaseDatasetLoader):
    """Parquet corpus loader.

    TODO(future): Implement Arrow/Parquet reading for large corpora.
    """

    def load(self, path: Path) -> list[BaseTask]:
        raise NotImplementedError("ParquetDatasetLoader will be implemented later")

    def list_task_ids(self, path: Path) -> list[str]:
        raise NotImplementedError("ParquetDatasetLoader will be implemented later")
