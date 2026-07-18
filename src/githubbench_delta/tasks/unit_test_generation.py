"""Unit test generation task stub."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class UnitTestGenerationTask(BaseTask):
    """Unit test generation task stub.

    TODO(phase-3): Add category-specific validation and prompt builders.
    """

    category: TaskCategory = TaskCategory.UNIT_TEST_GENERATION

    def expected_category(self) -> TaskCategory:
        return TaskCategory.UNIT_TEST_GENERATION
