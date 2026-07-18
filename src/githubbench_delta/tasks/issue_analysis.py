"""Issue analysis task."""

from __future__ import annotations

from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.base import BaseTask


class IssueAnalysisTask(BaseTask):
    """Analyze a GitHub issue and propose a grounded investigation plan."""

    category: TaskCategory = TaskCategory.ISSUE_ANALYSIS

    def expected_category(self) -> TaskCategory:
        return TaskCategory.ISSUE_ANALYSIS
