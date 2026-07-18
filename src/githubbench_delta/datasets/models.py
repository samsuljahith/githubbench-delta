"""Serialized task records used by dataset loaders."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from githubbench_delta.core.models import (
    Difficulty,
    ExpectedToolCall,
    FailureExample,
    GoldAnswer,
    RepositoryRef,
    TaskCategory,
    TaskInput,
    TaskMetadata,
    TaskOutput,
)


class SerializedTaskRecord(BaseModel):
    """Schema for a task as stored on disk (JSON/JSONL/YAML)."""

    id: str
    category: TaskCategory
    title: str = ""
    description: str = ""
    difficulty: Difficulty = Difficulty.MEDIUM
    language: str | None = None
    repository: RepositoryRef | None = None
    input: TaskInput
    expected_output: TaskOutput | None = None
    gold_answer: GoldAnswer | None = None
    gold_answers: list[GoldAnswer] = Field(default_factory=list)
    alternate_gold_answers: list[GoldAnswer] = Field(default_factory=list)
    difficulty_score: int | None = Field(default=None, ge=1, le=10)
    prompt_version: str = "1.0.0"
    expected_tool_calls: list[ExpectedToolCall] = Field(default_factory=list)
    failure_examples: list[FailureExample] = Field(default_factory=list)
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
    tags: list[str] = Field(default_factory=list)
    estimated_duration: float | None = None
    task_version: str = "1.0.0"
    dataset_version: str = "v1"
    prompt_ids: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
