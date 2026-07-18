"""Dataset and task corpus validators."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from githubbench_delta.core.errors import DatasetValidationError, TaskError
from githubbench_delta.core.models import Difficulty, GoldAnswerFormat, TaskCategory
from githubbench_delta.datasets.manifest import compute_content_hash
from githubbench_delta.datasets.metadata import DatasetMetadata
from githubbench_delta.datasets.repositories import resolve_local_path
from githubbench_delta.prompts.registry import load_default_prompt_registry
from githubbench_delta.tasks.base import BaseTask
from githubbench_delta.tasks.registry import list_task_categories
from githubbench_delta.tools.registry import create_default_github_registry

# Phase 3.5 production corpus targets (exact).
TARGET_CATEGORY_COUNTS: dict[str, int] = {
    "repository_search": 6,
    "architecture_understanding": 6,
    "code_explanation": 6,
    "bug_fix": 8,
    "commit_summary": 4,
    "readme_generation": 4,
    "documentation": 4,
    "pull_request_review": 5,
    "code_refactoring": 5,
    "dead_code_detection": 4,
    "issue_analysis": 4,
    "unit_test_generation": 4,
}

TARGET_DIFFICULTY_COUNTS: dict[str, int] = {
    Difficulty.EASY.value: 15,
    Difficulty.MEDIUM.value: 30,
    Difficulty.HARD.value: 15,
}

REQUIRED_LANGUAGES: frozenset[str] = frozenset({"python", "typescript", "go", "rust", "java"})
MIN_TASKS_PER_LANGUAGE = 6
TARGET_CORPUS_SIZE = 60


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


class DatasetValidator:
    """Validate loaded tasks and optional dataset metadata."""

    def __init__(
        self,
        *,
        require_local_repos: bool = False,
        base_path: Path | None = None,
        compatible_versions: list[str] | None = None,
        strict_corpus: bool = False,
    ) -> None:
        self.require_local_repos = require_local_repos or strict_corpus
        self.base_path = base_path
        self.compatible_versions = compatible_versions
        self.strict_corpus = strict_corpus

    def validate_tasks(
        self,
        tasks: list[BaseTask],
        *,
        metadata: DatasetMetadata | None = None,
        manifest_path: Path | None = None,
    ) -> list[BaseTask]:
        """Validate a task list; return the same list on success.

        Raises:
            DatasetValidationError: On any corpus-level or task-level failure.
        """

        if not tasks:
            raise DatasetValidationError("Dataset contains no tasks")

        known = set(list_task_categories())
        seen: set[str] = set()
        errors: list[str] = []

        for task in tasks:
            if task.id in seen:
                errors.append(f"Duplicate task id: {task.id}")
            seen.add(task.id)

            try:
                task.validate()
            except TaskError as exc:
                errors.append(str(exc))

            if task.category not in known:
                errors.append(f"Task {task.id}: unknown category {task.category}")

            if metadata is not None:
                if task.dataset_version != metadata.dataset_version:
                    errors.append(
                        f"Task {task.id}: dataset_version {task.dataset_version!r} "
                        f"!= metadata {metadata.dataset_version!r}"
                    )
                if (
                    metadata.compatible_task_versions
                    and task.task_version not in metadata.compatible_task_versions
                ):
                    errors.append(
                        f"Task {task.id}: task_version {task.task_version!r} "
                        f"not in compatible versions {metadata.compatible_task_versions}"
                    )

            if self.compatible_versions and task.dataset_version not in self.compatible_versions:
                errors.append(
                    f"Task {task.id}: incompatible dataset_version {task.dataset_version!r}"
                )

            for gold in [*task.gold_answers, *task.alternate_gold_answers]:
                if gold.format == GoldAnswerFormat.PATCH:
                    patch = (gold.patch or gold.content or "").strip()
                    if not patch:
                        errors.append(f"Task {task.id}: empty PATCH gold answer")

            if task.repository is not None and task.repository.local_path:
                local = resolve_local_path(task.repository, self.base_path)
                if local is None or not local.exists():
                    msg = (
                        f"Task {task.id}: repository local_path not found: "
                        f"{task.repository.local_path}"
                    )
                    if self.require_local_repos:
                        errors.append(msg)
                elif self.require_local_repos and not local.is_dir():
                    errors.append(f"Task {task.id}: local_path is not a directory: {local}")

        if errors:
            raise DatasetValidationError("Dataset validation failed:\n- " + "\n- ".join(errors))

        if self.strict_corpus:
            CorpusQualityValidator(base_path=self.base_path).validate(
                tasks,
                metadata=metadata,
                manifest_path=manifest_path,
            )

        return tasks

    def validate_category_coverage(
        self,
        tasks: list[BaseTask],
        required: set[TaskCategory] | None = None,
    ) -> None:
        """Optionally ensure required categories are present."""

        if not required:
            return
        present = {t.category for t in tasks}
        missing_cats: list[str] = []
        for req in required:
            if req in present:
                continue
            # satisfied via alias?
            if req == TaskCategory.ARCHITECTURE_EXPLANATION and (
                TaskCategory.ARCHITECTURE_UNDERSTANDING in present
            ):
                continue
            if req == TaskCategory.ARCHITECTURE_UNDERSTANDING and (
                TaskCategory.ARCHITECTURE_EXPLANATION in present
            ):
                continue
            if req == TaskCategory.CODE_REVIEW and TaskCategory.PULL_REQUEST_REVIEW in present:
                continue
            if req == TaskCategory.PULL_REQUEST_REVIEW and TaskCategory.CODE_REVIEW in present:
                continue
            if req == TaskCategory.REFACTORING and TaskCategory.CODE_REFACTORING in present:
                continue
            if req == TaskCategory.CODE_REFACTORING and TaskCategory.REFACTORING in present:
                continue
            missing_cats.append(req.value)
        if missing_cats:
            raise DatasetValidationError("Missing required categories: " + ", ".join(missing_cats))


class CorpusQualityValidator:
    """Strict quality gate for the Phase 3.5 production corpus."""

    def __init__(
        self,
        *,
        base_path: Path | None = None,
        target_category_counts: dict[str, int] | None = None,
        target_difficulty_counts: dict[str, int] | None = None,
        required_languages: frozenset[str] | None = None,
        min_tasks_per_language: int = MIN_TASKS_PER_LANGUAGE,
        target_size: int = TARGET_CORPUS_SIZE,
    ) -> None:
        self.base_path = base_path
        self.target_category_counts = target_category_counts or dict(TARGET_CATEGORY_COUNTS)
        self.target_difficulty_counts = target_difficulty_counts or dict(TARGET_DIFFICULTY_COUNTS)
        self.required_languages = required_languages or REQUIRED_LANGUAGES
        self.min_tasks_per_language = min_tasks_per_language
        self.target_size = target_size

    def validate(
        self,
        tasks: list[BaseTask],
        *,
        metadata: DatasetMetadata | None = None,
        manifest_path: Path | None = None,
    ) -> list[BaseTask]:
        """Run strict corpus checks.

        Raises:
            DatasetValidationError: When any quality rule fails.
        """

        errors: list[str] = []

        if len(tasks) != self.target_size:
            errors.append(f"Expected exactly {self.target_size} tasks, found {len(tasks)}")

        # Baseline structural validation with local repos required.
        try:
            DatasetValidator(
                require_local_repos=True,
                base_path=self.base_path,
                strict_corpus=False,
            ).validate_tasks(tasks, metadata=metadata)
        except DatasetValidationError as exc:
            errors.append(str(exc))

        cat_counts = Counter(t.category.value for t in tasks)
        for name, expected in self.target_category_counts.items():
            actual = cat_counts.get(name, 0)
            if actual != expected:
                errors.append(f"Category {name}: expected {expected}, found {actual}")
        unexpected = set(cat_counts) - set(self.target_category_counts)
        if unexpected:
            errors.append("Unexpected categories in corpus: " + ", ".join(sorted(unexpected)))

        diff_counts = Counter(t.difficulty.value for t in tasks)
        for name, expected in self.target_difficulty_counts.items():
            actual = diff_counts.get(name, 0)
            if actual != expected:
                errors.append(f"Difficulty {name}: expected {expected}, found {actual}")

        lang_counts = Counter((t.language or "").lower() for t in tasks)
        for lang in self.required_languages:
            if lang_counts.get(lang, 0) < self.min_tasks_per_language:
                errors.append(
                    f"Language {lang}: expected ≥{self.min_tasks_per_language} tasks, "
                    f"found {lang_counts.get(lang, 0)}"
                )

        registered_tools = set(create_default_github_registry().list_names())
        try:
            prompt_registry = load_default_prompt_registry(strict_hash=False)
            known_prompts = set(prompt_registry.list_ids())
        except Exception as exc:  # noqa: BLE001 — surface as validation error
            errors.append(f"Failed to load prompt registry: {exc}")
            known_prompts = set()

        titles: dict[str, str] = {}
        prompts: dict[str, str] = {}

        for task in tasks:
            if task.difficulty_score is None:
                errors.append(f"Task {task.id}: difficulty_score is required")
            elif not (1 <= task.difficulty_score <= 10):
                errors.append(
                    f"Task {task.id}: difficulty_score must be in 1..10, "
                    f"got {task.difficulty_score}"
                )

            if not task.prompt_version or not str(task.prompt_version).strip():
                errors.append(f"Task {task.id}: prompt_version is required")

            if not task.expected_tool_calls:
                errors.append(f"Task {task.id}: expected_tool_calls must be non-empty")
            else:
                for call in task.expected_tool_calls:
                    if call.name not in registered_tools:
                        errors.append(
                            f"Task {task.id}: unknown tool {call.name!r} "
                            f"(registered: {sorted(registered_tools)})"
                        )

            if len(task.failure_examples) < 2:
                errors.append(
                    f"Task {task.id}: need ≥2 failure_examples, found {len(task.failure_examples)}"
                )
            for idx, example in enumerate(task.failure_examples):
                if not example.kind:
                    errors.append(f"Task {task.id}: failure_examples[{idx}] missing kind")
                if not (example.description or "").strip():
                    errors.append(f"Task {task.id}: failure_examples[{idx}] missing description")

            if not task.gold_answers:
                errors.append(f"Task {task.id}: gold_answers must be non-empty")

            if not task.prompt_ids:
                errors.append(f"Task {task.id}: prompt_ids must be non-empty")
            else:
                for pid in task.prompt_ids:
                    if known_prompts and pid not in known_prompts:
                        errors.append(f"Task {task.id}: prompt_id {pid!r} not in prompt registry")

            if task.repository is None or not task.repository.local_path:
                errors.append(f"Task {task.id}: repository.local_path is required")
            else:
                local = resolve_local_path(task.repository, self.base_path)
                if local is None or not local.exists():
                    errors.append(
                        f"Task {task.id}: fixture path missing: {task.repository.local_path}"
                    )
                elif not (local / ".git").exists():
                    errors.append(f"Task {task.id}: fixture is not a git repo: {local}")

            title_key = _normalize_text(task.title or "")
            if title_key:
                if title_key in titles:
                    errors.append(
                        f"Duplicate title (normalized) for {task.id} and {titles[title_key]}"
                    )
                else:
                    titles[title_key] = task.id

            prompt_key = _normalize_text(task.input.prompt)
            if prompt_key in prompts:
                errors.append(
                    f"Duplicate prompt (normalized) for {task.id} and {prompts[prompt_key]}"
                )
            else:
                prompts[prompt_key] = task.id

        if manifest_path is not None and Path(manifest_path).is_file():
            try:
                data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
                expected_hash = data.get("content_hash")
                actual_hash = compute_content_hash(tasks)
                if expected_hash and expected_hash != actual_hash:
                    errors.append(
                        "Manifest content_hash mismatch: "
                        f"manifest={expected_hash[:16]}… recomputed={actual_hash[:16]}…"
                    )
                if data.get("task_count") not in (None, len(tasks)):
                    errors.append(
                        f"Manifest task_count {data.get('task_count')} != corpus size {len(tasks)}"
                    )
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"Failed to read manifest for hash check: {exc}")

        if errors:
            raise DatasetValidationError(
                "Strict corpus validation failed:\n- " + "\n- ".join(errors)
            )
        return tasks
