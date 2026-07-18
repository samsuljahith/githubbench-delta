"""Shared helpers for dataset loaders."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from githubbench_delta.core.errors import DatasetValidationError
from githubbench_delta.datasets.models import SerializedTaskRecord
from githubbench_delta.tasks.base import BaseTask
from githubbench_delta.tasks.registry import create_task


def record_to_task(data: dict[str, Any]) -> BaseTask:
    """Validate a raw mapping and instantiate the concrete task class."""

    try:
        record = SerializedTaskRecord.model_validate(data)
    except ValidationError as exc:
        raise DatasetValidationError(f"Invalid task record: {exc}") from exc

    payload = record.model_dump(exclude={"extra"}, exclude_none=False)
    category = payload.pop("category")
    # Drop empty optional collections that confuse defaults
    if not payload.get("gold_answers"):
        payload.pop("gold_answers", None)
    try:
        return create_task(category, **payload)
    except Exception as exc:  # noqa: BLE001
        raise DatasetValidationError(f"Failed to create task {record.id!r}: {exc}") from exc


def extract_task_id(data: dict[str, Any]) -> str:
    """Extract task id from a raw record."""

    task_id = data.get("id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise DatasetValidationError("Task record missing non-empty 'id'")
    return task_id
