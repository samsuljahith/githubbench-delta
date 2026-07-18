"""Versioned prompt templates for benchmark tasks."""

from githubbench_delta.prompts.hashing import hash_prompt_content
from githubbench_delta.prompts.models import PromptKind, PromptTemplate
from githubbench_delta.prompts.registry import (
    PromptRegistry,
    load_default_prompt_registry,
    load_prompts_from_dir,
)

__all__ = [
    "PromptKind",
    "PromptTemplate",
    "PromptRegistry",
    "hash_prompt_content",
    "load_default_prompt_registry",
    "load_prompts_from_dir",
]
