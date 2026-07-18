"""MetricContextFactory tests."""

from __future__ import annotations

from githubbench_delta.core.models import (
    AgentId,
    AgentResult,
    ExpectedToolCall,
    GoldAnswer,
    TaskInput,
    TaskOutput,
)
from githubbench_delta.pipeline.context_factory import MetricContextFactory
from githubbench_delta.tasks.registry import create_task


def test_factory_maps_gold_and_tools() -> None:
    task = create_task(
        "bug_fix",
        id="t1",
        input=TaskInput(prompt="fix it", files=["a.py"]),
        gold_answers=[
            GoldAnswer(content="patch", acceptance_criteria=["a.py"]),
        ],
        expected_tool_calls=[ExpectedToolCall(name="read_file")],
        alternate_gold_answers=[GoldAnswer(content="alt")],
    )
    ar = AgentResult(
        agent_id=AgentId.MINICPM,
        task_id="t1",
        success=True,
        output=TaskOutput(content="fixed a.py"),
    )
    ctx = MetricContextFactory().build(task, ar, seed=7, experiment_id="e1", run_id="r1")
    assert ctx.gold_answer is not None
    assert ctx.gold_answer.content == "patch"
    assert len(ctx.alternate_gold_answers) == 1
    assert ctx.expected_tool_calls[0].name == "read_file"
    assert ctx.task is not None
    assert ctx.task.files == ["a.py"]
    assert ctx.run_metadata["experiment_id"] == "e1"
    assert ctx.prompt == "fix it"
