"""Repository search task stub."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class RepositorySearchTask(BaseTask):
    """Repository search task stub.

    TODO(phase-3): Add category-specific validation and prompt builders.
    """

    category: TaskCategory = TaskCategory.REPOSITORY_SEARCH

    def expected_category(self) -> TaskCategory:
        return TaskCategory.REPOSITORY_SEARCH
