"""DatasetValidator tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from githubbench_delta.core.errors import DatasetValidationError
from githubbench_delta.core.models import GoldAnswer, GoldAnswerFormat, TaskCategory, TaskInput
from githubbench_delta.datasets.factory import load_tasks
from githubbench_delta.datasets.manifest import load_dataset_metadata
from githubbench_delta.datasets.validators import CorpusQualityValidator, DatasetValidator
from githubbench_delta.tasks.registry import create_task

ROOT = Path(__file__).resolve().parents[2]


def test_duplicate_ids_rejected() -> None:
    t1 = create_task(TaskCategory.BUG_FIX, id="dup", input=TaskInput(prompt="a"))
    t2 = create_task(TaskCategory.BUG_FIX, id="dup", input=TaskInput(prompt="b"))
    with pytest.raises(DatasetValidationError, match="Duplicate"):
        DatasetValidator().validate_tasks([t1, t2])


def test_bad_patch_gold_rejected() -> None:
    task = create_task(
        TaskCategory.BUG_FIX,
        id="p1",
        input=TaskInput(prompt="fix"),
        gold_answers=[
            GoldAnswer(format=GoldAnswerFormat.TEXT, content="ok"),
        ],
    )
    # Bypass create_task validation by mutating after creation
    task.gold_answers = [GoldAnswer(format=GoldAnswerFormat.PATCH, content="", patch="")]
    with pytest.raises(DatasetValidationError, match="PATCH"):
        DatasetValidator().validate_tasks([task])


def test_strict_corpus_flag_on_dataset_validator() -> None:
    tasks = load_tasks(ROOT / "datasets" / "v1" / "tasks.jsonl")
    meta = load_dataset_metadata(ROOT / "datasets" / "v1" / "dataset.yaml")
    DatasetValidator(base_path=ROOT, strict_corpus=True).validate_tasks(
        tasks,
        metadata=meta,
        manifest_path=ROOT / "datasets" / "v1" / "manifest.json",
    )


def test_corpus_quality_validator_rejects_wrong_size() -> None:
    tasks = load_tasks(ROOT / "datasets" / "v1" / "tasks.jsonl")[:5]
    with pytest.raises(DatasetValidationError, match="exactly 60"):
        CorpusQualityValidator(base_path=ROOT).validate(tasks)
