"""Dataset loader tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from githubbench_delta.core.errors import DatasetValidationError
from githubbench_delta.datasets.factory import get_loader_for_path, load_tasks
from githubbench_delta.datasets.loaders import (
    CSVDatasetLoader,
    ParquetDatasetLoader,
)


def _minimal_task(task_id: str = "t1") -> dict:
    return {
        "id": task_id,
        "category": "bug_fix",
        "title": "Bug",
        "input": {"prompt": "Fix the bug"},
        "dataset_version": "v1",
        "task_version": "1.0.0",
    }


def test_jsonl_and_json_and_yaml_loaders(tmp_path: Path) -> None:
    records = [_minimal_task("a"), _minimal_task("b")]
    jsonl = tmp_path / "t.jsonl"
    jsonl.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    tasks = load_tasks(jsonl)
    assert [t.id for t in tasks] == ["a", "b"]

    json_path = tmp_path / "t.json"
    json_path.write_text(json.dumps({"tasks": records}), encoding="utf-8")
    assert len(load_tasks(json_path)) == 2

    yaml_path = tmp_path / "t.yaml"
    yaml_path.write_text(yaml.safe_dump(records), encoding="utf-8")
    assert get_loader_for_path(yaml_path).list_task_ids(yaml_path) == ["a", "b"]


def test_invalid_jsonl_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text("{not json\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError):
        load_tasks(path)


def test_missing_prompt_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps([{"id": "x", "category": "bug_fix", "input": {"prompt": "   "}}]),
        encoding="utf-8",
    )
    with pytest.raises(DatasetValidationError):
        load_tasks(path)


def test_parquet_csv_stubs() -> None:
    with pytest.raises(NotImplementedError):
        ParquetDatasetLoader().load(Path("x.parquet"))
    with pytest.raises(NotImplementedError):
        CSVDatasetLoader().list_task_ids(Path("x.csv"))


def test_v1_corpus_loads() -> None:
    root = Path(__file__).resolve().parents[2]
    tasks = load_tasks(root / "datasets" / "v1" / "tasks.jsonl")
    assert len(tasks) == 60
