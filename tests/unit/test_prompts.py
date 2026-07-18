"""Prompt versioning and hashing tests."""

from __future__ import annotations

import pytest

from githubbench_delta.prompts.hashing import hash_prompt_content
from githubbench_delta.prompts.models import PromptKind, PromptTemplate
from githubbench_delta.prompts.registry import load_default_prompt_registry


def test_default_prompts_load_and_verify() -> None:
    registry = load_default_prompt_registry(strict_hash=True)
    assert len(registry) >= 4
    system = registry.get("system.default")
    assert system.kind == PromptKind.SYSTEM
    assert system.version == "1.0.0"
    assert system.verify_hash(strict=True)


def test_hash_mismatch_strict() -> None:
    prompt = PromptTemplate(
        id="x",
        kind=PromptKind.TASK,
        content="hello",
        content_hash="deadbeef",
    )
    with pytest.raises(ValueError):
        prompt.verify_hash(strict=True)
    assert hash_prompt_content("hello") != "deadbeef"
