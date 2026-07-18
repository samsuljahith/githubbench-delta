"""README generation task stub."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class ReadmeGenerationTask(BaseTask):
    """README generation task stub.

    TODO(phase-3): Add category-specific validation and prompt builders.
    """

    category: TaskCategory = TaskCategory.README_GENERATION

    def expected_category(self) -> TaskCategory:
        return TaskCategory.README_GENERATION
