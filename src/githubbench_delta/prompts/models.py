"""Prompt template models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from githubbench_delta.prompts.hashing import hash_prompt_content


class PromptKind(StrEnum):
    """Prompt role / placement in the agent message stack."""

    SYSTEM = "system"
    DEVELOPER = "developer"
    TASK = "task"
    TOOL = "tool"


class PromptTemplate(BaseModel):
    """Versioned prompt template with content hashing."""

    id: str
    kind: PromptKind
    version: str = "1.0.0"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    content_hash: str | None = None

    @model_validator(mode="after")
    def _ensure_hash(self) -> PromptTemplate:
        computed = hash_prompt_content(self.content)
        if self.content_hash is None:
            self.content_hash = computed
        return self

    def verify_hash(self, *, strict: bool = True) -> bool:
        """Verify stored hash matches content.

        Returns:
            True when hashes match.

        Raises:
            ValueError: When ``strict`` and hashes diverge.
        """

        computed = hash_prompt_content(self.content)
        ok = self.content_hash == computed
        if strict and not ok:
            raise ValueError(
                f"Prompt {self.id}@{self.version} hash mismatch: "
                f"stored={self.content_hash} computed={computed}"
            )
        return ok
