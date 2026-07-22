"""Validate twin task sidecar specs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from githubbench_delta.memorization.helpers import deep_get, normalize_prompt
from githubbench_delta.memorization.models import TwinTaskSpec


class TwinValidationError(ValueError):
    """Raised when a twin spec fails validation."""


class TwinValidator:
    """Ensure twins link to parents, keep gold/repo, and use distinct prompts."""

    def validate_spec(
        self,
        twin: TwinTaskSpec | dict[str, Any],
        *,
        parent: dict[str, Any] | None = None,
    ) -> list[str]:
        """Return list of error strings (empty = valid)."""

        errors: list[str] = []
        if isinstance(twin, TwinTaskSpec):
            record = twin.record
            parent_id = twin.parent_task_id
            twin_id = twin.id
        else:
            record = twin
            twin_id = str(twin.get("id", ""))
            parent_id = str(
                deep_get(twin, "metadata", "extra", "parent_task_id")
                or twin.get("parent_task_id")
                or ""
            )

        if not twin_id:
            errors.append("Twin missing id.")
        if not parent_id:
            errors.append("Twin missing metadata.extra.parent_task_id.")
        if twin_id and parent_id and twin_id == parent_id:
            errors.append("Twin id must differ from parent_task_id.")

        twin_prompt = str(deep_get(record, "input", "prompt") or "")
        if not twin_prompt.strip():
            errors.append("Twin prompt is empty.")

        if parent is not None:
            parent_prompt = str(deep_get(parent, "input", "prompt") or "")
            if (
                twin_prompt
                and parent_prompt
                and normalize_prompt(twin_prompt) == normalize_prompt(parent_prompt)
            ):
                errors.append("Twin prompt must differ from parent prompt.")
            parent_gold = parent.get("gold_answer")
            twin_gold = record.get("gold_answer")
            if parent_gold is not None and twin_gold != parent_gold:
                errors.append("Twin gold_answer must match parent.")
            parent_repo = parent.get("repository")
            twin_repo = record.get("repository")
            if parent_repo is not None and twin_repo != parent_repo:
                errors.append("Twin repository must match parent.")
            if str(parent.get("id", "")) != parent_id and parent_id:
                errors.append(
                    f"parent_task_id {parent_id!r} does not match parent id "
                    f"{parent.get('id')!r}."
                )
        return errors

    def validate_catalog(
        self,
        specs: list[TwinTaskSpec],
        *,
        parents: dict[str, dict[str, Any]] | None = None,
    ) -> list[TwinTaskSpec]:
        """Return only valid specs; raise if any invalid when parents provided."""

        valid: list[TwinTaskSpec] = []
        problems: list[str] = []
        for spec in specs:
            parent = (parents or {}).get(spec.parent_task_id)
            errs = self.validate_spec(spec, parent=parent)
            if errs:
                problems.append(f"{spec.id}: " + "; ".join(errs))
            else:
                valid.append(spec)
        if problems and parents is not None:
            raise TwinValidationError(
                f"{len(problems)} twin validation error(s): " + " | ".join(problems[:5])
            )
        return valid

    def load_twins_jsonl(self, path: Path | str) -> list[TwinTaskSpec]:
        p = Path(path)
        specs: list[TwinTaskSpec] = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            parent_id = str(deep_get(record, "metadata", "extra", "parent_task_id") or "")
            specs.append(
                TwinTaskSpec(
                    id=str(record.get("id", "")),
                    parent_task_id=parent_id,
                    twin_kind=str(
                        deep_get(record, "metadata", "extra", "twin_kind") or "paraphrase"
                    ),
                    generator_version=str(
                        deep_get(record, "metadata", "extra", "generator_version") or "unknown"
                    ),
                    record=record,
                )
            )
        return specs
