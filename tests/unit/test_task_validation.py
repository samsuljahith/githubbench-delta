"""BaseTask validation and gold normalization."""

from __future__ import annotations

import pytest

from githubbench_delta.core.errors import TaskError
from githubbench_delta.core.models import (
    Difficulty,
    GoldAnswer,
    GoldAnswerFormat,
    TaskCategory,
    TaskInput,
)
from githubbench_delta.tasks.registry import create_task


def test_gold_answer_normalizes_to_list() -> None:
    task = create_task(
        TaskCategory.BUG_FIX,
        id="g1",
        input=TaskInput(prompt="fix it"),
        gold_answer=GoldAnswer(content="done", format=GoldAnswerFormat.TEXT),
    )
    assert len(task.gold_answers) == 1
    assert task.gold_answer is not None
    assert task.gold_answer.content == "done"


def test_patch_gold_requires_content() -> None:
    with pytest.raises(TaskError):
        create_task(
            TaskCategory.BUG_FIX,
            id="g2",
            input=TaskInput(prompt="fix it"),
            gold_answers=[GoldAnswer(format=GoldAnswerFormat.PATCH, content="", patch="")],
        )


def test_optional_expected_tools_and_failure_examples() -> None:
    from githubbench_delta.core.models import ExpectedToolCall, FailureExample, FailureExampleKind

    task = create_task(
        TaskCategory.BUG_FIX,
        id="traj-1",
        input=TaskInput(prompt="fix with tools"),
        expected_tool_calls=[
            ExpectedToolCall(name="list_files", arguments={"path": "."}),
            ExpectedToolCall(name="read_file", arguments={"path": "src/mathutil.py"}),
        ],
        failure_examples=[
            FailureExample(
                kind=FailureExampleKind.HALLUCINATED_API,
                description="Invents a non-existent helper",
                example="Calls delete_all() which does not exist",
                related_metrics=["hallucinated_api", "planning_quality"],
            ),
            FailureExample(
                kind=FailureExampleKind.UNSAFE_EDIT,
                description="Edits unrelated files",
                related_metrics=["blast_radius", "safe_failure"],
            ),
        ],
    )
    assert len(task.expected_tool_calls) == 2
    assert task.expected_tool_calls[0].name == "list_files"
    assert task.failure_examples[0].kind == FailureExampleKind.HALLUCINATED_API
    payload = task.to_serializable()
    assert "expected_tool_calls" in payload
    assert "failure_examples" in payload


def test_tasks_without_optional_trajectory_fields_still_load() -> None:
    task = create_task(
        TaskCategory.DOCUMENTATION,
        id="plain-1",
        input=TaskInput(prompt="document add"),
    )
    assert task.expected_tool_calls == []
    assert task.failure_examples == []


def test_alias_category_architecture_understanding() -> None:
    task = create_task(
        TaskCategory.ARCHITECTURE_UNDERSTANDING,
        id="arch1",
        title="Arch",
        description="desc",
        difficulty=Difficulty.EASY,
        language="python",
        input=TaskInput(prompt="Explain architecture"),
        tags=["arch"],
    )
    assert task.category == TaskCategory.ARCHITECTURE_UNDERSTANDING
    task.validate()
    data = task.to_serializable()
    assert data["id"] == "arch1"
    assert data["task_version"] == "1.0.0"
