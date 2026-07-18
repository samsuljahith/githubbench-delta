"""Single-trial pipeline: agent → trajectory → MetricContext → EvaluationEngine."""

from __future__ import annotations

from typing import Protocol

from githubbench_delta.core.config import AppConfig, RetryConfig, load_config
from githubbench_delta.core.models import AgentId, AgentResult, EvaluationResult
from githubbench_delta.core.retry import RetryPolicy, retry_async
from githubbench_delta.metrics.engine import EvaluationEngine
from githubbench_delta.pipeline.cache import make_cache_key
from githubbench_delta.pipeline.context_factory import MetricContextFactory
from githubbench_delta.pipeline.models import CachedEvaluation, WorkUnit
from githubbench_delta.storage.results.base import ResultStore
from githubbench_delta.tasks.base import BaseTask


class SupportsRunTask(Protocol):
    """Minimal agent surface required by PipelineRunner."""

    agent_id: AgentId

    async def run_task(self, task: BaseTask, *, trial_index: int = 0) -> AgentResult: ...


class PipelineRunner:
    """Execute one work unit through the evaluation pipeline."""

    def __init__(
        self,
        *,
        evaluation_engine: EvaluationEngine | None = None,
        context_factory: MetricContextFactory | None = None,
        result_store: ResultStore | None = None,
        app_config: AppConfig | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.app_config = app_config or load_config()
        self.engine = evaluation_engine or EvaluationEngine(app_config=self.app_config)
        self.factory = context_factory or MetricContextFactory()
        self.store = result_store
        self.retry_config = retry_config or self.app_config.runtime.retry

    async def run_unit(
        self,
        *,
        task: BaseTask,
        agent: SupportsRunTask | None,
        unit: WorkUnit,
        experiment_id: str,
        run_id: str,
        seed: int,
        peer_results: list[AgentResult] | None = None,
        peer_evaluations: list[EvaluationResult] | None = None,
        injected_result: AgentResult | None = None,
        use_cache: bool = True,
        persist: bool = True,
    ) -> tuple[AgentResult, EvaluationResult]:
        """Run agent (or use injected result), evaluate, optionally persist."""

        agent_result = injected_result
        if agent_result is None:
            if agent is None:
                raise ValueError("agent or injected_result is required")
            agent_result = await self._run_agent_with_retry(
                agent, task, trial_index=unit.trial_index
            )

        if use_cache and self.store is not None:
            key = make_cache_key(
                task_id=unit.task_id,
                agent_id=str(unit.agent_id),
                trial_index=unit.trial_index,
                seed=seed,
                agent_result=agent_result,
            )
            cached = self.store.get_cache_entry(key)
            if cached is not None:
                evaluation = EvaluationResult.model_validate(cached.evaluation_result)
                if persist:
                    self._persist(
                        experiment_id=experiment_id,
                        run_id=run_id,
                        unit=unit,
                        agent_result=agent_result,
                        evaluation=evaluation,
                        cache_key=None,
                    )
                return agent_result, evaluation

        ctx = self.factory.build(
            task,
            agent_result,
            trial_index=unit.trial_index,
            seed=seed,
            peer_results=peer_results,
            peer_evaluations=peer_evaluations,
            experiment_id=experiment_id,
            run_id=run_id,
        )
        evaluation = self.engine.evaluate(ctx)

        cache_key = None
        if use_cache:
            cache_key = make_cache_key(
                task_id=unit.task_id,
                agent_id=str(unit.agent_id),
                trial_index=unit.trial_index,
                seed=seed,
                agent_result=agent_result,
            )
        if persist and self.store is not None:
            self._persist(
                experiment_id=experiment_id,
                run_id=run_id,
                unit=unit,
                agent_result=agent_result,
                evaluation=evaluation,
                cache_key=cache_key,
            )
        return agent_result, evaluation

    async def evaluate_only(
        self,
        *,
        task: BaseTask,
        agent_result: AgentResult,
        unit: WorkUnit,
        seed: int,
        peer_results: list[AgentResult] | None = None,
        peer_evaluations: list[EvaluationResult] | None = None,
        experiment_id: str = "",
        run_id: str = "",
    ) -> EvaluationResult:
        """Re-evaluate an existing agent result (e.g. peer attachment pass)."""

        ctx = self.factory.build(
            task,
            agent_result,
            trial_index=unit.trial_index,
            seed=seed,
            peer_results=peer_results,
            peer_evaluations=peer_evaluations,
            experiment_id=experiment_id or None,
            run_id=run_id or None,
        )
        return self.engine.evaluate(ctx)

    async def _run_agent_with_retry(
        self,
        agent: SupportsRunTask,
        task: BaseTask,
        *,
        trial_index: int,
    ) -> AgentResult:
        cfg = self.retry_config
        policy = RetryPolicy(
            max_attempts=cfg.max_attempts,
            base_delay_s=cfg.base_delay_s,
            max_delay_s=cfg.max_delay_s,
            exponential_base=cfg.exponential_base,
            jitter=cfg.jitter,
        )

        async def _once() -> AgentResult:
            return await agent.run_task(task, trial_index=trial_index)

        try:
            return await retry_async(_once, policy)
        except Exception:  # noqa: BLE001 — still return a failed AgentResult if possible
            from githubbench_delta.core.models import TaskOutput

            return AgentResult(
                agent_id=agent.agent_id,
                task_id=task.id,
                trial_index=trial_index,
                success=False,
                output=TaskOutput(content=""),
                error="agent_run_failed_after_retries",
            )

    def _persist(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        agent_result: AgentResult,
        evaluation: EvaluationResult,
        cache_key: str | None,
    ) -> None:
        assert self.store is not None
        self.store.save_trajectory(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            agent_result=agent_result,
        )
        self.store.save_evaluation(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            evaluation=evaluation,
            agent_result=agent_result,
        )
        self.store.mark_unit_complete(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            success=True,
        )
        if cache_key is not None:
            self.store.put_cache_entry(
                CachedEvaluation(
                    cache_key=cache_key,
                    agent_result=agent_result.model_dump(mode="json"),
                    evaluation_result=evaluation.model_dump(mode="json"),
                )
            )
