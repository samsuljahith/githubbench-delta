"""Dead code detection task stub."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class DeadCodeDetectionTask(BaseTask):
    """Dead code detection task stub.

    TODO(phase-3): Add category-specific validation and prompt builders.
    """

    category: TaskCategory = TaskCategory.DEAD_CODE_DETECTION

    def expected_category(self) -> TaskCategory:
        return TaskCategory.DEAD_CODE_DETECTION
