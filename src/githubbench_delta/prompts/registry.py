"""Prompt template registry and file loading."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import yaml

from githubbench_delta.core.errors import RegistryError
from githubbench_delta.prompts.models import PromptTemplate


class PromptRegistry:
    """Register and resolve versioned prompt templates."""

    def __init__(self) -> None:
        self._prompts: dict[str, PromptTemplate] = {}

    def register(self, prompt: PromptTemplate, *, strict_hash: bool = True) -> None:
        """Register a prompt; optionally verify content hash."""

        prompt.verify_hash(strict=strict_hash)
        self._prompts[prompt.id] = prompt

    def get(self, prompt_id: str) -> PromptTemplate:
        """Lookup a prompt by id."""

        try:
            return self._prompts[prompt_id]
        except KeyError as exc:
            raise RegistryError(f"Unknown prompt id: {prompt_id}") from exc

    def list_ids(self) -> list[str]:
        """Return registered prompt ids sorted."""

        return sorted(self._prompts)

    def resolve_many(self, prompt_ids: list[str]) -> list[PromptTemplate]:
        """Resolve an ordered list of prompt ids."""

        return [self.get(pid) for pid in prompt_ids]

    def __len__(self) -> int:
        return len(self._prompts)


def load_prompts_from_dir(path: Path | str, *, strict_hash: bool = True) -> PromptRegistry:
    """Load all ``.yaml``/``.yml`` prompt files from a directory."""

    root = Path(path)
    registry = PromptRegistry()
    if not root.is_dir():
        return registry
    for file in sorted(root.glob("*.yaml")) + sorted(root.glob("*.yml")):
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "prompts" in data:
            items = data["prompts"]
        else:
            items = [data]
        for item in items:
            registry.register(PromptTemplate.model_validate(item), strict_hash=strict_hash)
    return registry


def load_default_prompt_registry(*, strict_hash: bool = True) -> PromptRegistry:
    """Load packaged v1 prompt templates."""

    try:
        base = resources.files("githubbench_delta.prompts.templates").joinpath("v1")
        # Traversable → Path when possible
        root = Path(str(base))
        if root.is_dir():
            return load_prompts_from_dir(root, strict_hash=strict_hash)
    except (TypeError, FileNotFoundError, ModuleNotFoundError):
        pass
    # Fallback for editable installs / source tree
    fallback = Path(__file__).resolve().parent / "templates" / "v1"
    return load_prompts_from_dir(fallback, strict_hash=strict_hash)
