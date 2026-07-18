"""Code review task stub."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class CodeReviewTask(BaseTask):
    """Code review task stub.

    TODO(phase-3): Add category-specific validation and prompt builders.
    """

    category: TaskCategory = TaskCategory.CODE_REVIEW

    def expected_category(self) -> TaskCategory:
        return TaskCategory.CODE_REVIEW
