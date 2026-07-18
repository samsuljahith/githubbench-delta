"""PipelineRunner unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from githubbench_delta.core.config import load_config
from githubbench_delta.core.models import (
    AgentId,
    AgentResult,
    GoldAnswer,
    TaskInput,
    TaskOutput,
)
from githubbench_delta.pipeline.models import WorkUnit
from githubbench_delta.pipeline.runner import PipelineRunner
from githubbench_delta.storage.results import create_result_store
from githubbench_delta.tasks.registry import create_task


class MockAgent:
    """Duck-typed agent for pipeline tests (no provider)."""

    agent_id = AgentId.CODEX
    display_name = "Mock"

    def __init__(self, text: str = "widgetcli/store.py add") -> None:
        self._text = text

    async def run_task(self, task, *, trial_index: int = 0) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            trial_index=trial_index,
            success=True,
            output=TaskOutput(content=self._text),
        )


@pytest.mark.asyncio
async def test_pipeline_runner_evaluate_and_persist(tmp_path: Path) -> None:
    cfg = load_config()
    store = create_result_store(
        experiment_dir=tmp_path / "exp",
        sqlite_path=tmp_path / "db.sqlite",
    )
    runner = PipelineRunner(app_config=cfg, result_store=store)
    task = create_task(
        "repository_search",
        id="gb-test-001",
        input=TaskInput(prompt="find add", files=["widgetcli/store.py"]),
        gold_answers=[
            GoldAnswer(
                content="widgetcli/store.py add",
                acceptance_criteria=["widgetcli/store.py", "add"],
            )
        ],
    )
    unit = WorkUnit(task_id=task.id, agent_id="codex", trial_index=0)
    ar, ev = await runner.run_unit(
        task=task,
        agent=MockAgent(),
        unit=unit,
        experiment_id="exp",
        run_id="run1",
        seed=42,
        use_cache=True,
        persist=True,
    )
    assert ar.success
    assert ev.overall_score is not None
    assert "task_resolution" in ev.metric_results
    assert store.is_unit_complete(experiment_id="exp", run_id="run1", unit=unit)

    # Cache hit path
    ar2, ev2 = await runner.run_unit(
        task=task,
        agent=MockAgent(),
        unit=unit,
        experiment_id="exp",
        run_id="run1",
        seed=42,
        use_cache=True,
        persist=True,
    )
    assert ev2.overall_score == ev.overall_score
    store.close()
