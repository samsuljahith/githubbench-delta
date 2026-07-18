"""GitHub engineering task abstractions."""

from githubbench_delta.tasks.architecture_explanation import ArchitectureExplanationTask
from githubbench_delta.tasks.base import BaseTask
from githubbench_delta.tasks.bug_fix import BugFixTask
from githubbench_delta.tasks.catalog import TaskCatalog
from githubbench_delta.tasks.code_explanation import CodeExplanationTask
from githubbench_delta.tasks.code_review import CodeReviewTask
from githubbench_delta.tasks.commit_summary import CommitSummaryTask
from githubbench_delta.tasks.dead_code_detection import DeadCodeDetectionTask
from githubbench_delta.tasks.documentation import DocumentationTask
from githubbench_delta.tasks.issue_analysis import IssueAnalysisTask
from githubbench_delta.tasks.pr_generation import PRGenerationTask
from githubbench_delta.tasks.readme_generation import ReadmeGenerationTask
from githubbench_delta.tasks.refactoring import RefactoringTask
from githubbench_delta.tasks.registry import (
    create_task,
    get_task_class,
    list_task_categories,
    register_task_class,
)
from githubbench_delta.tasks.repository_search import RepositorySearchTask
from githubbench_delta.tasks.unit_test_generation import UnitTestGenerationTask

__all__ = [
    "BaseTask",
    "TaskCatalog",
    "ArchitectureExplanationTask",
    "BugFixTask",
    "CodeExplanationTask",
    "CodeReviewTask",
    "CommitSummaryTask",
    "DeadCodeDetectionTask",
    "DocumentationTask",
    "IssueAnalysisTask",
    "PRGenerationTask",
    "ReadmeGenerationTask",
    "RefactoringTask",
    "RepositorySearchTask",
    "UnitTestGenerationTask",
    "create_task",
    "get_task_class",
    "list_task_categories",
    "register_task_class",
]
