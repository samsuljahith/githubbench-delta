"""Benchmark loading, filtering, and deterministic subset selection."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from githubbench_delta.benchmark.sampling import sample_deterministic, shuffle_deterministic
from githubbench_delta.core.models import Difficulty, TaskCategory
from githubbench_delta.datasets.factory import get_loader_for_path, load_tasks
from githubbench_delta.datasets.manifest import load_dataset_metadata
from githubbench_delta.datasets.metadata import DatasetMetadata
from githubbench_delta.datasets.validators import DatasetValidator
from githubbench_delta.prompts.registry import PromptRegistry, load_default_prompt_registry
from githubbench_delta.tasks.base import BaseTask
from githubbench_delta.tasks.catalog import TaskCatalog


class DistributedExecutor(Protocol):
    """Future distributed execution backend.

    TODO(phase-5): Implement remote/worker fan-out for large benchmarks.
    """

    def submit(self, tasks: list[BaseTask]) -> list[str]:
        """Submit tasks for remote execution; return job ids."""
        ...


class BenchmarkRunner:
    """Load and prepare benchmark task sets for agent execution."""

    def __init__(
        self,
        *,
        prompt_registry: PromptRegistry | None = None,
        validate: bool = True,
        base_path: Path | None = None,
    ) -> None:
        self.prompt_registry = prompt_registry or load_default_prompt_registry()
        self.validate = validate
        self.base_path = base_path
        self.catalog = TaskCatalog()
        self.metadata: DatasetMetadata | None = None

    def load_dataset(self, dataset_dir: Path | str) -> TaskCatalog:
        """Load a dataset directory (``dataset.yaml`` + task file)."""

        root = Path(dataset_dir)
        meta_path = root / "dataset.yaml"
        if not meta_path.is_file():
            meta_path = root / "dataset.yml"
        if meta_path.is_file():
            self.metadata = load_dataset_metadata(meta_path)
            task_file = root / self.metadata.task_file
        else:
            self.metadata = None
            # Prefer jsonl then json then yaml
            task_file = next(
                (
                    p
                    for p in (
                        root / "tasks.jsonl",
                        root / "tasks.json",
                        root / "tasks.yaml",
                    )
                    if p.is_file()
                ),
                root / "tasks.jsonl",
            )

        tasks = load_tasks(task_file)
        # Also load optional per-category YAML snippets under tasks/
        tasks_dir = root / "tasks"
        if tasks_dir.is_dir():
            for path in sorted(tasks_dir.glob("*.yaml")) + sorted(tasks_dir.glob("*.yml")):
                tasks.extend(get_loader_for_path(path).load(path))

        if self.validate:
            DatasetValidator(
                base_path=self.base_path or root,
                require_local_repos=False,
            ).validate_tasks(tasks, metadata=self.metadata)

        self._attach_prompts(tasks)
        self.catalog = TaskCatalog(tasks)
        return self.catalog

    def load_file(self, path: Path | str) -> TaskCatalog:
        """Load tasks from a single dataset file."""

        tasks = load_tasks(path)
        if self.validate:
            DatasetValidator(base_path=self.base_path).validate_tasks(tasks)
        self._attach_prompts(tasks)
        self.catalog = TaskCatalog(tasks)
        return self.catalog

    def _attach_prompts(self, tasks: list[BaseTask]) -> None:
        for task in tasks:
            if not task.prompt_ids:
                task.prompt_ids = [
                    "system.default",
                    "developer.default",
                    "task.generic",
                    "tool.readonly",
                ]
            # Resolve to ensure ids exist
            self.prompt_registry.resolve_many(task.prompt_ids)

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
        """Filter the loaded catalog."""

        return self.catalog.filter(
            difficulty=difficulty,
            language=language,
            category=category,
            repository=repository,
            dataset_version=dataset_version,
            tags=tags,
        )

    def single(self, task_id: str) -> BaseTask:
        """Return one task by id."""

        task = self.catalog.get(task_id)
        if task is None:
            raise KeyError(f"Unknown task id: {task_id}")
        return task

    def batch(
        self,
        task_ids: list[str] | None = None,
        *,
        n: int | None = None,
        seed: int = 42,
        shuffle: bool = True,
        **filter_kwargs,
    ) -> list[BaseTask]:
        """Return a batch of tasks (by ids, sample size, and/or filters)."""

        if task_ids is not None:
            tasks = [self.single(tid) for tid in task_ids]
        else:
            tasks = self.filter(**filter_kwargs) if filter_kwargs else self.catalog.all()
        if n is not None:
            return sample_deterministic(tasks, n, seed)
        if shuffle:
            return shuffle_deterministic(tasks, seed)
        return tasks

    def full(self, *, seed: int | None = None) -> list[BaseTask]:
        """Return the full benchmark task list, optionally shuffled."""

        tasks = self.catalog.all()
        if seed is not None:
            return shuffle_deterministic(tasks, seed)
        return tasks

    def prepare_distributed(self, executor: DistributedExecutor) -> list[str]:
        """Submit the full catalog to a future distributed executor.

        TODO(phase-5): Wire real worker pools / queues.
        """

        return executor.submit(self.catalog.all())
