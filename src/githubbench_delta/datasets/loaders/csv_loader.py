"""CSV dataset loader stub."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.datasets.base import BaseDatasetLoader
from githubbench_delta.tasks.base import BaseTask


class CSVDatasetLoader(BaseDatasetLoader):
    """CSV corpus loader.

    TODO(future): Implement CSV reading with column→task mapping.
    """

    def load(self, path: Path) -> list[BaseTask]:
        raise NotImplementedError("CSVDatasetLoader will be implemented later")

    def list_task_ids(self, path: Path) -> list[str]:
        raise NotImplementedError("CSVDatasetLoader will be implemented later")
