"""Task type registry mapping categories to concrete task classes."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.errors import RegistryError
from githubbench_delta.core.models import TaskCategory
from githubbench_delta.tasks.architecture_explanation import ArchitectureExplanationTask
from githubbench_delta.tasks.base import BaseTask
from githubbench_delta.tasks.bug_fix import BugFixTask
from githubbench_delta.tasks.code_explanation import CodeExplanationTask
from githubbench_delta.tasks.code_review import CodeReviewTask
from githubbench_delta.tasks.commit_summary import CommitSummaryTask
from githubbench_delta.tasks.dead_code_detection import DeadCodeDetectionTask
from githubbench_delta.tasks.documentation import DocumentationTask
from githubbench_delta.tasks.issue_analysis import IssueAnalysisTask
from githubbench_delta.tasks.pr_generation import PRGenerationTask
from githubbench_delta.tasks.readme_generation import ReadmeGenerationTask
from githubbench_delta.tasks.refactoring import RefactoringTask
from githubbench_delta.tasks.repository_search import RepositorySearchTask
from githubbench_delta.tasks.unit_test_generation import UnitTestGenerationTask

_TASK_CLASSES: dict[TaskCategory, type[BaseTask]] = {
    TaskCategory.REPOSITORY_SEARCH: RepositorySearchTask,
    TaskCategory.ARCHITECTURE_EXPLANATION: ArchitectureExplanationTask,
    TaskCategory.ARCHITECTURE_UNDERSTANDING: ArchitectureExplanationTask,
    TaskCategory.CODE_EXPLANATION: CodeExplanationTask,
    TaskCategory.COMMIT_SUMMARY: CommitSummaryTask,
    TaskCategory.BUG_FIX: BugFixTask,
    TaskCategory.README_GENERATION: ReadmeGenerationTask,
    TaskCategory.DOCUMENTATION: DocumentationTask,
    TaskCategory.CODE_REVIEW: CodeReviewTask,
    TaskCategory.PULL_REQUEST_REVIEW: CodeReviewTask,
    TaskCategory.REFACTORING: RefactoringTask,
    TaskCategory.CODE_REFACTORING: RefactoringTask,
    TaskCategory.PR_GENERATION: PRGenerationTask,
    TaskCategory.UNIT_TEST_GENERATION: UnitTestGenerationTask,
    TaskCategory.DEAD_CODE_DETECTION: DeadCodeDetectionTask,
    TaskCategory.ISSUE_ANALYSIS: IssueAnalysisTask,
}


def register_task_class(category: TaskCategory, cls: type[BaseTask]) -> None:
    """Register or replace a task class for a category."""

    _TASK_CLASSES[category] = cls


def list_task_categories() -> list[TaskCategory]:
    """Return all registered task categories in enum order."""

    return [cat for cat in TaskCategory if cat in _TASK_CLASSES]


def get_task_class(category: TaskCategory | str) -> type[BaseTask]:
    """Lookup the concrete task class for a category."""

    key = TaskCategory(category)
    try:
        return _TASK_CLASSES[key]
    except KeyError as exc:
        raise RegistryError(f"No task class registered for {key}") from exc


def create_task(category: TaskCategory | str, **kwargs: Any) -> BaseTask:
    """Instantiate and validate a task for the given category."""

    key = TaskCategory(category)
    cls = get_task_class(key)
    if "category" not in kwargs:
        kwargs["category"] = key
    task = cls(**kwargs)
    task.validate()
    return task
