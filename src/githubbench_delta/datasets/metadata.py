"""Dataset metadata and versioning models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DatasetMetadata(BaseModel):
    """Metadata describing a versioned dataset corpus."""

    name: str
    dataset_version: str = "v1"
    description: str = ""
    author: str = ""
    license: str = "Apache-2.0"
    created_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    task_file: str = "tasks.jsonl"
    compatible_task_versions: list[str] = Field(default_factory=lambda: ["1.0.0"])
