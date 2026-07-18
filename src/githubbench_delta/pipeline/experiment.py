"""ExperimentRunner — batch / parallel / multi-agent / multi-trial orchestration."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any

from githubbench_delta.agents.registry import create_agents_from_app_config
from githubbench_delta.benchmark.runner import BenchmarkRunner
from githubbench_delta.core.config import AppConfig, load_config
from githubbench_delta.core.models import AgentId, AgentResult, EvaluationResult, RunSummary
from githubbench_delta.pipeline.cache import unit_seed
from githubbench_delta.pipeline.experiment_manager import ExperimentManager
from githubbench_delta.pipeline.models import (
    ExperimentManifest,
    ExperimentSpec,
    ExperimentStatus,
    ProgressEvent,
    WorkUnit,
)
from githubbench_delta.pipeline.run_manager import RunManager
from githubbench_delta.pipeline.runner import PipelineRunner, SupportsRunTask
from githubbench_delta.storage.results import create_result_store
from githubbench_delta.storage.results.composite import CompositeResultStore
from githubbench_delta.tasks.base import BaseTask

ProgressCallback = Callable[[ProgressEvent], None]


class ExperimentRunner:
    """Orchestrate dataset → agents → evaluation → storage."""

    def __init__(
        self,
        *,
        app_config: AppConfig | None = None,
        benchmark_runner: BenchmarkRunner | None = None,
        agents: dict[AgentId | str, SupportsRunTask] | None = None,
        experiment_manager: ExperimentManager | None = None,
    ) -> None:
        self.app_config = app_config or load_config()
        self.benchmark = benchmark_runner or BenchmarkRunner(
            base_path=Path.cwd(),
            validate=True,
        )
        self._agents = agents
        self.experiments = experiment_manager or ExperimentManager(app_config=self.app_config)

    def _resolve_agents(self, agent_ids: list[str]) -> dict[str, SupportsRunTask]:
        if self._agents is not None:
            pool = {str(k): v for k, v in self._agents.items()}
        else:
            pool = {str(k): v for k, v in create_agents_from_app_config(self.app_config).items()}
        if not agent_ids:
            return pool
        missing = [a for a in agent_ids if a not in pool]
        if missing:
            raise KeyError(f"Unknown agent ids: {missing}")
        return {a: pool[a] for a in agent_ids}

    def _load_tasks(self, spec: ExperimentSpec) -> list[BaseTask]:
        self.benchmark.load_dataset(spec.dataset_path)
        if spec.task_ids:
            return [self.benchmark.single(tid) for tid in spec.task_ids]
        return self.benchmark.full(seed=spec.seed)

    async def run(self, spec: ExperimentSpec) -> ExperimentManifest:
        """Run a full experiment from ``ExperimentSpec``."""

        tasks = self._load_tasks(spec)
        agents = self._resolve_agents(spec.agent_ids)
        if not agents:
            raise ValueError("No agents configured for experiment")
        if not tasks:
            raise ValueError("No tasks selected for experiment")

        pipeline_cfg = self.app_config.runtime.pipeline
        max_concurrency = spec.max_concurrency or pipeline_cfg.max_concurrency
        resume = spec.resume if spec.resume is not None else pipeline_cfg.resume
        use_cache = spec.use_cache if spec.use_cache is not None else pipeline_cfg.cache_evaluations

        manifest = self.experiments.create(spec, task_ids=[t.id for t in tasks])
        exp_dir = self.experiments.experiment_dir(manifest.experiment_id)
        store: CompositeResultStore = create_result_store(
            experiment_dir=exp_dir,
            sqlite_path=self.app_config.runtime.storage.sqlite_path,
        )
        self.experiments._sqlite = store.sqlite  # type: ignore[attr-defined]
        run_mgr = RunManager(exp_dir, sqlite_store=store.sqlite)

        units = self._build_units(tasks, list(agents), spec.trial_count)
        run = run_mgr.create(
            experiment_id=manifest.experiment_id,
            units_total=len(units),
            seed=spec.seed,
        )
        pipeline = PipelineRunner(
            app_config=self.app_config,
            result_store=store,
        )
        task_by_id = {t.id: t for t in tasks}

        self.experiments.set_status(manifest.experiment_id, ExperimentStatus.RUNNING)
        run_mgr.mark_running(run)

        agent_results: dict[str, AgentResult] = {}
        evaluations: dict[str, EvaluationResult] = {}
        interrupted = False

        try:
            await self._execute_units(
                units=units,
                task_by_id=task_by_id,
                agents=agents,
                pipeline=pipeline,
                store=store,
                run_mgr=run_mgr,
                run=run,
                experiment_id=manifest.experiment_id,
                seed=spec.seed,
                max_concurrency=max_concurrency,
                resume=resume,
                use_cache=use_cache,
                dry_run=spec.dry_run,
                agent_results=agent_results,
                evaluations=evaluations,
            )
            # Peer attachment pass: re-evaluate with peer_results per task
            await self._peer_pass(
                tasks=tasks,
                agents=list(agents),
                trial_count=spec.trial_count,
                agent_results=agent_results,
                evaluations=evaluations,
                pipeline=pipeline,
                store=store,
                experiment_id=manifest.experiment_id,
                run_id=run.run_id,
                seed=spec.seed,
            )
        except (asyncio.CancelledError, KeyboardInterrupt):
            interrupted = True
            raise
        finally:
            run = run_mgr.load()
            run_mgr.finalize(run, interrupted=interrupted)
            status = (
                ExperimentStatus.INTERRUPTED
                if interrupted
                else (
                    ExperimentStatus.FAILED
                    if run.units_done == 0 and run.units_failed
                    else ExperimentStatus.COMPLETED
                )
            )
            self.experiments.set_status(manifest.experiment_id, status)
            store.close()

        return self.experiments.load(manifest.experiment_id)

    async def run_single_task(
        self,
        dataset_path: Path | str,
        task_id: str,
        *,
        agent_ids: list[str] | None = None,
        trial_count: int = 1,
        seed: int = 42,
        **kwargs: Any,
    ) -> ExperimentManifest:
        return await self.run(
            ExperimentSpec(
                dataset_path=dataset_path,
                task_ids=[task_id],
                agent_ids=agent_ids or [],
                trial_count=trial_count,
                seed=seed,
                **kwargs,
            )
        )

    async def run_dataset(
        self,
        dataset_path: Path | str,
        *,
        agent_ids: list[str] | None = None,
        trial_count: int | None = None,
        seed: int | None = None,
        **kwargs: Any,
    ) -> ExperimentManifest:
        return await self.run(
            ExperimentSpec(
                dataset_path=dataset_path,
                agent_ids=agent_ids or [],
                trial_count=trial_count or self.app_config.runtime.trial_count,
                seed=seed if seed is not None else self.app_config.runtime.seed,
                **kwargs,
            )
        )

    async def run_comparison(
        self,
        dataset_path: Path | str,
        *,
        agent_ids: list[str],
        task_ids: list[str] | None = None,
        trial_count: int = 1,
        seed: int = 42,
        **kwargs: Any,
    ) -> ExperimentManifest:
        return await self.run(
            ExperimentSpec(
                dataset_path=dataset_path,
                agent_ids=agent_ids,
                task_ids=task_ids,
                trial_count=trial_count,
                seed=seed,
                **kwargs,
            )
        )

    def build_run_summary(
        self,
        *,
        run_id: str,
        seed: int,
        evaluations: list[EvaluationResult],
        agent_ids: list[str],
        task_ids: list[str],
    ) -> RunSummary:
        overall: dict[str, float] = {}
        groups: dict[str, list[float]] = defaultdict(list)
        for ev in evaluations:
            aid = str(ev.trial.agent_id)
            if ev.overall_score is not None:
                overall.setdefault(aid, 0.0)
                # running mean later — collect then average
            for g, s in ev.group_scores.items():
                groups[g].append(s)
        # Mean overall per agent
        per_agent: dict[str, list[float]] = defaultdict(list)
        for ev in evaluations:
            if ev.overall_score is not None:
                per_agent[str(ev.trial.agent_id)].append(ev.overall_score)
        overall_scores = {a: sum(v) / len(v) for a, v in per_agent.items() if v}
        group_scores = {g: sum(v) / len(v) for g, v in groups.items() if v}
        return RunSummary(
            run_id=run_id,
            seed=seed,
            agent_ids=[AgentId(a) for a in agent_ids],
            task_ids=task_ids,
            evaluations=evaluations,
            overall_scores=overall_scores,
            group_scores=group_scores,
        )

    @staticmethod
    def _build_units(
        tasks: list[BaseTask],
        agent_ids: list[str],
        trial_count: int,
    ) -> list[WorkUnit]:
        units: list[WorkUnit] = []
        for task in tasks:
            for agent_id in agent_ids:
                for trial in range(trial_count):
                    units.append(
                        WorkUnit(
                            task_id=task.id,
                            agent_id=agent_id,
                            trial_index=trial,
                        )
                    )
        return units

    async def _execute_units(
        self,
        *,
        units: list[WorkUnit],
        task_by_id: dict[str, BaseTask],
        agents: dict[str, SupportsRunTask],
        pipeline: PipelineRunner,
        store: CompositeResultStore,
        run_mgr: RunManager,
        run: Any,
        experiment_id: str,
        seed: int,
        max_concurrency: int,
        resume: bool,
        use_cache: bool,
        dry_run: bool,
        agent_results: dict[str, AgentResult],
        evaluations: dict[str, EvaluationResult],
        on_progress: ProgressCallback | None = None,
    ) -> None:
        sem = asyncio.Semaphore(max(1, max_concurrency))
        done = 0
        total = len(units)

        async def _one(unit: WorkUnit) -> None:
            nonlocal done, run
            async with sem:
                if resume and store.is_unit_complete(
                    experiment_id=experiment_id,
                    run_id=run.run_id,
                    unit=unit,
                ):
                    loaded = store.load_agent_result(unit)
                    if loaded is not None:
                        agent_results[unit.key()] = loaded
                    done += 1
                    if on_progress:
                        on_progress(
                            ProgressEvent(
                                units_done=done,
                                units_total=total,
                                current_unit=unit.key(),
                                message="skipped (resume)",
                            )
                        )
                    return

                task = task_by_id[unit.task_id]
                agent = agents[str(unit.agent_id)]
                u_seed = unit_seed(seed, unit.task_id, str(unit.agent_id), unit.trial_index)
                try:
                    if dry_run:
                        from githubbench_delta.core.models import TaskOutput

                        injected = AgentResult(
                            agent_id=AgentId(str(unit.agent_id)),
                            task_id=unit.task_id,
                            trial_index=unit.trial_index,
                            success=True,
                            output=TaskOutput(
                                content=(
                                    (task.gold_answer.content if task.gold_answer else "")
                                    or (
                                        task.gold_answers[0].content
                                        if task.gold_answers
                                        else "dry-run"
                                    )
                                )
                            ),
                        )
                        ar, ev = await pipeline.run_unit(
                            task=task,
                            agent=None,
                            unit=unit,
                            experiment_id=experiment_id,
                            run_id=run.run_id,
                            seed=u_seed,
                            injected_result=injected,
                            use_cache=use_cache,
                            persist=True,
                        )
                    else:
                        ar, ev = await pipeline.run_unit(
                            task=task,
                            agent=agent,
                            unit=unit,
                            experiment_id=experiment_id,
                            run_id=run.run_id,
                            seed=u_seed,
                            use_cache=use_cache,
                            persist=True,
                        )
                    agent_results[unit.key()] = ar
                    evaluations[unit.key()] = ev
                    run = run_mgr.mark_unit_progress(run_mgr.load(), unit, success=True)
                except Exception as exc:  # noqa: BLE001
                    store.mark_unit_complete(
                        experiment_id=experiment_id,
                        run_id=run.run_id,
                        unit=unit,
                        success=False,
                        error=str(exc),
                    )
                    run = run_mgr.mark_unit_progress(
                        run_mgr.load(), unit, success=False, error=str(exc)
                    )
                finally:
                    done += 1
                    if on_progress:
                        on_progress(
                            ProgressEvent(
                                units_done=done,
                                units_total=total,
                                current_unit=unit.key(),
                            )
                        )

        await asyncio.gather(*[_one(u) for u in units])

    async def _peer_pass(
        self,
        *,
        tasks: list[BaseTask],
        agents: list[str],
        trial_count: int,
        agent_results: dict[str, AgentResult],
        evaluations: dict[str, EvaluationResult],
        pipeline: PipelineRunner,
        store: CompositeResultStore,
        experiment_id: str,
        run_id: str,
        seed: int,
    ) -> None:
        """Re-evaluate each unit with peer agent results for the same task."""

        for task in tasks:
            peers = [
                agent_results[WorkUnit(task_id=task.id, agent_id=a, trial_index=t).key()]
                for a in agents
                for t in range(trial_count)
                if WorkUnit(task_id=task.id, agent_id=a, trial_index=t).key() in agent_results
            ]
            peer_evals = [
                evaluations[WorkUnit(task_id=task.id, agent_id=a, trial_index=t).key()]
                for a in agents
                for t in range(trial_count)
                if WorkUnit(task_id=task.id, agent_id=a, trial_index=t).key() in evaluations
            ]
            for a in agents:
                for t in range(trial_count):
                    unit = WorkUnit(task_id=task.id, agent_id=a, trial_index=t)
                    key = unit.key()
                    if key not in agent_results:
                        continue
                    primary = agent_results[key]
                    peer_rs = [p for p in peers if p is not primary]
                    peer_ev = [
                        e
                        for e in peer_evals
                        if not (
                            e.trial.task_id == unit.task_id
                            and str(e.trial.agent_id) == str(unit.agent_id)
                            and e.trial.trial_index == unit.trial_index
                        )
                    ]
                    u_seed = unit_seed(seed, unit.task_id, str(unit.agent_id), unit.trial_index)
                    ev = await pipeline.evaluate_only(
                        task=task,
                        agent_result=primary,
                        unit=unit,
                        seed=u_seed,
                        peer_results=peer_rs,
                        peer_evaluations=peer_ev,
                        experiment_id=experiment_id,
                        run_id=run_id,
                    )
                    evaluations[key] = ev
                    store.save_evaluation(
                        experiment_id=experiment_id,
                        run_id=run_id,
                        unit=unit,
                        evaluation=ev,
                        agent_result=primary,
                    )
