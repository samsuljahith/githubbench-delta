"""Code explanation task."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class CodeExplanationTask(BaseTask):
    """Explain selected code behavior, APIs, or control flow."""

    category: TaskCategory = TaskCategory.CODE_EXPLANATION

    def expected_category(self) -> TaskCategory:
        return TaskCategory.CODE_EXPLANATION
