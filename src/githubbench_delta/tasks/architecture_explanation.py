"""Architecture explanation task stub."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class ArchitectureExplanationTask(BaseTask):
    """Architecture explanation task stub.

    TODO(phase-3): Add category-specific validation and prompt builders.
    """

    category: TaskCategory = TaskCategory.ARCHITECTURE_EXPLANATION

    def expected_category(self) -> TaskCategory:
        return TaskCategory.ARCHITECTURE_EXPLANATION
