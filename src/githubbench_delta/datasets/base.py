"""Dataset loader interface for GitHubBench-Delta task corpora."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from githubbench_delta.tasks.base import BaseTask


class BaseDatasetLoader(ABC):
    """Load and validate task datasets from disk."""

    @abstractmethod
    def load(self, path: Path) -> list[BaseTask]:
        """Load tasks from ``path``."""

    @abstractmethod
    def list_task_ids(self, path: Path) -> list[str]:
        """List task ids available at ``path`` without fully hydrating."""
