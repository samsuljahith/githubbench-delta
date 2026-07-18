"""Task interface contract for GitHub engineering workloads."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, model_validator

from githubbench_delta.core.errors import TaskError
from githubbench_delta.core.models import (
    Difficulty,
    ExpectedToolCall,
    FailureExample,
    GoldAnswer,
    GoldAnswerFormat,
    RepositoryRef,
    TaskCategory,
    TaskInput,
    TaskMetadata,
    TaskOutput,
)


class BaseTask(BaseModel, ABC):
    """Production GitHub engineering task.

    Every task exposes identity, difficulty, category, repository binding,
    input, gold answers, versions, and metadata. Concrete subclasses customize
    prompt shaping via ``expected_category`` / ``to_prompt``.
    """

    id: str
    title: str = ""
    description: str = ""
    category: TaskCategory
    difficulty: Difficulty = Difficulty.MEDIUM
    language: str | None = None
    repository: RepositoryRef | None = None
    input: TaskInput
    expected_output: TaskOutput | None = None
    gold_answer: GoldAnswer | None = None
    gold_answers: list[GoldAnswer] = Field(default_factory=list)
    alternate_gold_answers: list[GoldAnswer] = Field(
        default_factory=list,
        description="Additional acceptable solutions beyond the primary gold answer.",
    )
    difficulty_score: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description="Estimated difficulty on a 1–10 scale.",
    )
    prompt_version: str = "1.0.0"
    expected_tool_calls: list[ExpectedToolCall] = Field(
        default_factory=list,
        description=(
            "Optional ordered gold trajectory of tool invocations for "
            "Tool Economy / Planning Quality evaluation."
        ),
    )
    failure_examples: list[FailureExample] = Field(
        default_factory=list,
        description=(
            "Optional known incorrect/unsafe behaviors for Hallucinated API, "
            "Blast Radius, Safe Failure, and related metrics."
        ),
    )
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
    tags: list[str] = Field(default_factory=list)
    estimated_duration: float | None = Field(default=None, ge=0.0)
    task_version: str = "1.0.0"
    dataset_version: str = "v1"
    prompt_ids: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _normalize_fields(self) -> BaseTask:
        if not self.title and self.metadata.title:
            self.title = self.metadata.title
        if not self.description and self.metadata.description:
            self.description = self.metadata.description
        if self.language is None and self.metadata.language:
            self.language = self.metadata.language
        if not self.tags and self.metadata.tags:
            self.tags = list(self.metadata.tags)
        if self.gold_answer is not None and not self.gold_answers:
            self.gold_answers = [self.gold_answer]
        elif self.gold_answers and self.gold_answer is None:
            self.gold_answer = self.gold_answers[0]
        if self.repository is not None:
            if self.repository.url and not self.input.repository_url:
                self.input.repository_url = self.repository.url
            if self.repository.commit_sha and not self.input.repository_ref:
                self.input.repository_ref = self.repository.commit_sha
            elif self.repository.branch and not self.input.repository_ref:
                self.input.repository_ref = self.repository.branch
            if self.repository.local_path:
                self.input.context.setdefault("repo_path", self.repository.local_path)
        return self

    def validate(self) -> None:  # type: ignore[override]
        """Validate required fields before execution or dataset acceptance.

        Raises:
            TaskError: If the task definition is incomplete or inconsistent.
        """

        if not self.id:
            raise TaskError("Task id must be non-empty")
        if not self.input.prompt.strip():
            raise TaskError(f"Task {self.id}: input.prompt must be non-empty")
        # Allow alias categories that map to the same family class.
        if self.category != self.expected_category() and not self._category_compatible(
            self.category, self.expected_category()
        ):
            raise TaskError(
                f"Task {self.id}: category {self.category} does not match "
                f"expected {self.expected_category()}"
            )
        for gold in [*self.gold_answers, *self.alternate_gold_answers]:
            self._validate_gold(gold)
        if self.difficulty_score is not None and not (1 <= self.difficulty_score <= 10):
            raise TaskError(f"Task {self.id}: difficulty_score must be in 1..10")

    def _category_compatible(self, actual: TaskCategory, expected: TaskCategory) -> bool:
        aliases = {
            TaskCategory.ARCHITECTURE_UNDERSTANDING: TaskCategory.ARCHITECTURE_EXPLANATION,
            TaskCategory.ARCHITECTURE_EXPLANATION: TaskCategory.ARCHITECTURE_UNDERSTANDING,
            TaskCategory.PULL_REQUEST_REVIEW: TaskCategory.CODE_REVIEW,
            TaskCategory.CODE_REVIEW: TaskCategory.PULL_REQUEST_REVIEW,
            TaskCategory.CODE_REFACTORING: TaskCategory.REFACTORING,
            TaskCategory.REFACTORING: TaskCategory.CODE_REFACTORING,
        }
        return actual == expected or aliases.get(actual) == expected

    def _validate_gold(self, gold: GoldAnswer) -> None:
        if gold.format == GoldAnswerFormat.PATCH:
            patch = gold.patch or gold.content
            if not patch.strip():
                raise TaskError(f"Task {self.id}: PATCH gold answer is empty")
        if (
            gold.format == GoldAnswerFormat.STRUCTURED
            and not gold.structured
            and not gold.content.strip()
        ):
            raise TaskError(f"Task {self.id}: STRUCTURED gold answer missing structured payload")
        if gold.format == GoldAnswerFormat.JSON and not (gold.content or gold.structured):
            raise TaskError(f"Task {self.id}: JSON gold answer is empty")
        if gold.format == GoldAnswerFormat.CODE and not gold.content.strip():
            raise TaskError(f"Task {self.id}: CODE gold answer is empty")

    @abstractmethod
    def expected_category(self) -> TaskCategory:
        """Return the canonical category this task class is responsible for."""

    def to_prompt(self) -> str:
        """Build the prompt string presented to an agent."""

        parts: list[str] = []
        if self.title:
            parts.append(f"# {self.title}")
        if self.description:
            parts.append(self.description.strip())
        parts.append(self.input.prompt.strip())
        if self.input.repository_url:
            parts.append(f"Repository: {self.input.repository_url}")
        if self.input.repository_ref:
            parts.append(f"Ref: {self.input.repository_ref}")
        if self.input.files:
            parts.append("Files:\n" + "\n".join(f"- {path}" for path in self.input.files))
        return "\n\n".join(parts)

    def to_serializable(self) -> dict[str, Any]:
        """Return a JSON-serializable dict representation of this task."""

        return self.model_dump(mode="json")
