"""Detect dataset format and return the appropriate loader."""

from __future__ import annotations

from pathlib import Path

from githubbench_delta.core.errors import DatasetValidationError
from githubbench_delta.datasets.base import BaseDatasetLoader
from githubbench_delta.datasets.loaders import (
    CSVDatasetLoader,
    JSONDatasetLoader,
    JSONLDatasetLoader,
    ParquetDatasetLoader,
    YAMLDatasetLoader,
)


def get_loader_for_path(path: Path | str) -> BaseDatasetLoader:
    """Return a loader instance based on file suffix."""

    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".json":
        return JSONDatasetLoader()
    if suffix == ".jsonl":
        return JSONLDatasetLoader()
    if suffix in {".yaml", ".yml"}:
        return YAMLDatasetLoader()
    if suffix == ".parquet":
        return ParquetDatasetLoader()
    if suffix == ".csv":
        return CSVDatasetLoader()
    raise DatasetValidationError(f"Unsupported dataset format: {path.suffix!r}")


def load_tasks(path: Path | str) -> list:
    """Convenience: detect format and load tasks from ``path``."""

    path = Path(path)
    return get_loader_for_path(path).load(path)
