"""ExperimentRunner orchestration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from githubbench_delta.core.config import load_config
from githubbench_delta.core.models import AgentId, AgentResult, TaskOutput
from githubbench_delta.pipeline.experiment import ExperimentRunner
from githubbench_delta.pipeline.models import ExperimentSpec, ExperimentStatus, WorkUnit
from githubbench_delta.storage.results import create_result_store


class MockAgent:
    agent_id: AgentId

    def __init__(self, agent_id: AgentId, text: str) -> None:
        self.agent_id = agent_id
        self._text = text
        self.calls = 0

    async def run_task(self, task, *, trial_index: int = 0) -> AgentResult:
        self.calls += 1
        return AgentResult(
            agent_id=self.agent_id,
            task_id=task.id,
            trial_index=trial_index,
            success=True,
            output=TaskOutput(content=self._text),
        )


@pytest.mark.asyncio
async def test_experiment_dry_run_single_task(tmp_path: Path) -> None:
    cfg = load_config()
    cfg.runtime.pipeline.results_dir = tmp_path / "experiments"
    root = Path(__file__).resolve().parents[3]
    dataset = root / "datasets" / "v1"
    runner = ExperimentRunner(
        app_config=cfg,
        agents={
            AgentId.CODEX: MockAgent(AgentId.CODEX, "widgetcli/store.py add"),
        },
    )
    manifest = await runner.run(
        ExperimentSpec(
            dataset_path=dataset,
            agent_ids=["codex"],
            task_ids=["gb-repository-search-001"],
            trial_count=2,
            seed=1,
            max_concurrency=2,
            dry_run=True,
            resume=False,
            use_cache=True,
            name="unit-test-exp",
        )
    )
    assert manifest.status == ExperimentStatus.COMPLETED
    exp_dir = cfg.runtime.pipeline.results_dir / manifest.experiment_id
    assert (exp_dir / "experiment.json").is_file()
    assert (exp_dir / "run.json").is_file()
    assert (exp_dir / "evaluation_results.json").is_file()
    assert (exp_dir / "trajectory.jsonl").is_file()
    run = json.loads((exp_dir / "run.json").read_text(encoding="utf-8"))
    assert run["units_done"] == 2


@pytest.mark.asyncio
async def test_resume_marks_units_complete(tmp_path: Path) -> None:
    cfg = load_config()
    cfg.runtime.pipeline.results_dir = tmp_path / "experiments"
    root = Path(__file__).resolve().parents[3]
    agent = MockAgent(AgentId.CODEX, "widgetcli/store.py add")
    runner = ExperimentRunner(app_config=cfg, agents={AgentId.CODEX: agent})
    manifest = await runner.run(
        ExperimentSpec(
            dataset_path=root / "datasets" / "v1",
            agent_ids=["codex"],
            task_ids=["gb-repository-search-001"],
            trial_count=1,
            seed=2,
            dry_run=False,
            resume=True,
            name="resume-test",
        )
    )
    exp_dir = cfg.runtime.pipeline.results_dir / manifest.experiment_id
    run = json.loads((exp_dir / "run.json").read_text(encoding="utf-8"))
    store = create_result_store(
        experiment_dir=exp_dir,
        sqlite_path=tmp_path / "resume.db",
    )
    # Copy completion into this store from jsonl units file
    unit = WorkUnit(task_id="gb-repository-search-001", agent_id="codex", trial_index=0)
    assert store.jsonl.is_unit_complete(
        experiment_id=manifest.experiment_id,
        run_id=run["run_id"],
        unit=unit,
    )
    assert agent.calls == 1
    store.close()


@pytest.mark.asyncio
async def test_multi_agent_comparison(tmp_path: Path) -> None:
    cfg = load_config()
    cfg.runtime.pipeline.results_dir = tmp_path / "experiments"
    root = Path(__file__).resolve().parents[3]
    runner = ExperimentRunner(
        app_config=cfg,
        agents={
            AgentId.MINICPM: MockAgent(AgentId.MINICPM, "local answer widgetcli/store.py"),
            AgentId.CODEX: MockAgent(AgentId.CODEX, "hosted answer widgetcli/store.py"),
        },
    )
    manifest = await runner.run_comparison(
        root / "datasets" / "v1",
        agent_ids=["minicpm", "codex"],
        task_ids=["gb-repository-search-001"],
        trial_count=1,
        seed=3,
        dry_run=True,
        max_concurrency=2,
    )
    assert manifest.status == ExperimentStatus.COMPLETED
    assert set(manifest.agent_ids) == {"minicpm", "codex"}
