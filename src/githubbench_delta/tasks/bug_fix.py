"""Bug fix task stub."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class BugFixTask(BaseTask):
    """Bug fix task stub.

    TODO(phase-3): Add category-specific validation and prompt builders.
    """

    category: TaskCategory = TaskCategory.BUG_FIX

    def expected_category(self) -> TaskCategory:
        return TaskCategory.BUG_FIX
