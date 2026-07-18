"""Task catalog for discovery and filtering of loaded benchmark tasks."""

from __future__ import annotations

from collections.abc import Iterable

from githubbench_delta.core.models import Difficulty, TaskCategory
from githubbench_delta.tasks.base import BaseTask


class TaskCatalog:
    """In-memory index of loaded ``BaseTask`` instances."""

    def __init__(self, tasks: Iterable[BaseTask] | None = None) -> None:
        self._tasks: list[BaseTask] = list(tasks or [])

    def add(self, task: BaseTask) -> None:
        """Register a task instance."""

        self._tasks.append(task)

    def extend(self, tasks: Iterable[BaseTask]) -> None:
        """Register multiple task instances."""

        self._tasks.extend(tasks)

    def __len__(self) -> int:
        return len(self._tasks)

    def all(self) -> list[BaseTask]:
        """Return all tasks in insertion order."""

        return list(self._tasks)

    def get(self, task_id: str) -> BaseTask | None:
        """Lookup a task by id."""

        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    def filter(
        self,
        *,
        difficulty: Difficulty | str | None = None,
        language: str | None = None,
        category: TaskCategory | str | None = None,
        repository: str | None = None,
        dataset_version: str | None = None,
        tags: list[str] | None = None,
    ) -> list[BaseTask]:
        """Filter tasks by metadata dimensions (AND semantics)."""

        diff = Difficulty(difficulty) if isinstance(difficulty, str) else difficulty
        cat = TaskCategory(category) if isinstance(category, str) else category
        required_tags = set(tags or [])

        results: list[BaseTask] = []
        for task in self._tasks:
            if diff is not None and task.difficulty != diff:
                continue
            if language is not None and (task.language or "").lower() != language.lower():
                continue
            if cat is not None and task.category != cat:
                continue
            if dataset_version is not None and task.dataset_version != dataset_version:
                continue
            if required_tags and not required_tags.issubset(set(task.tags)):
                continue
            if repository is not None:
                repo_vals = {
                    (task.repository.url if task.repository else None),
                    (task.repository.local_path if task.repository else None),
                    task.input.repository_url,
                }
                if repository not in {v for v in repo_vals if v}:
                    continue
            results.append(task)
        return results

    def categories(self) -> list[TaskCategory]:
        """Distinct categories present in the catalog."""

        return sorted({t.category for t in self._tasks}, key=lambda c: c.value)

    def languages(self) -> list[str]:
        """Distinct languages present in the catalog."""

        return sorted({(t.language or "unknown") for t in self._tasks})
