"""Phase 3.5 corpus distribution, fixtures, schema, and strict validation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from githubbench_delta.core.models import GoldAnswer, GoldAnswerFormat, TaskCategory, TaskInput
from githubbench_delta.datasets.factory import load_tasks
from githubbench_delta.datasets.manifest import load_dataset_metadata
from githubbench_delta.datasets.validators import (
    TARGET_CATEGORY_COUNTS,
    TARGET_CORPUS_SIZE,
    TARGET_DIFFICULTY_COUNTS,
    CorpusQualityValidator,
)
from githubbench_delta.tasks.registry import create_task
from githubbench_delta.tools.registry import create_default_github_registry

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "datasets" / "v1"
FIXTURES = ROOT / "datasets" / "fixtures"
FIXTURE_NAMES = (
    "py_cli",
    "py_rag",
    "ts_frontend",
    "go_rest_api",
    "rust_service",
    "java_backend",
)


def test_corpus_v1_size_and_distribution() -> None:
    tasks = load_tasks(V1 / "tasks.jsonl")
    assert len(tasks) == TARGET_CORPUS_SIZE
    assert Counter(t.category.value for t in tasks) == TARGET_CATEGORY_COUNTS
    assert Counter(t.difficulty.value for t in tasks) == TARGET_DIFFICULTY_COUNTS
    langs = Counter((t.language or "").lower() for t in tasks)
    for lang in ("python", "typescript", "go", "rust", "java"):
        assert langs[lang] >= 6, lang


def test_corpus_strict_validation() -> None:
    tasks = load_tasks(V1 / "tasks.jsonl")
    meta = load_dataset_metadata(V1 / "dataset.yaml")
    CorpusQualityValidator(base_path=ROOT).validate(
        tasks,
        metadata=meta,
        manifest_path=V1 / "manifest.json",
    )


def test_schema_difficulty_score_and_prompt_version() -> None:
    task = create_task(
        TaskCategory.BUG_FIX,
        id="schema-roundtrip",
        input=TaskInput(prompt="fix me"),
        difficulty_score=7,
        prompt_version="1.2.3",
        gold_answers=[GoldAnswer(format=GoldAnswerFormat.CODE, content="def fix():\n    pass\n")],
        alternate_gold_answers=[
            GoldAnswer(format=GoldAnswerFormat.TEXT, content="alternative fix")
        ],
    )
    dumped = task.model_dump(mode="json")
    assert dumped["difficulty_score"] == 7
    assert dumped["prompt_version"] == "1.2.3"
    assert dumped["gold_answers"][0]["format"] == "code"
    assert len(dumped["alternate_gold_answers"]) == 1


def test_fixture_repos_exist() -> None:
    """Fixtures are vendored as normal directories (no nested .git) for cloneability."""
    for name in FIXTURE_NAMES:
        path = FIXTURES / name
        assert path.is_dir(), name
        assert (path / "README.md").is_file() or (path / "README").is_file(), name
        assert (path / "ISSUES.md").is_file(), name


def test_expected_tools_are_registered() -> None:
    registered = set(create_default_github_registry().list_names())
    tasks = load_tasks(V1 / "tasks.jsonl")
    for task in tasks:
        for call in task.expected_tool_calls:
            assert call.name in registered, (task.id, call.name)
