"""PR generation task stub."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class PRGenerationTask(BaseTask):
    """PR generation task stub.

    TODO(phase-3): Add category-specific validation and prompt builders.
    """

    category: TaskCategory = TaskCategory.PR_GENERATION

    def expected_category(self) -> TaskCategory:
        return TaskCategory.PR_GENERATION
