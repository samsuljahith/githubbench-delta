"""Build MetricContext from BaseTask + AgentResult without modifying metrics."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.models import AgentResult, EvaluationResult, TrialKey
from githubbench_delta.metrics.base import MetricContext, TaskSnapshot
from githubbench_delta.tasks.base import BaseTask


class MetricContextFactory:
    """Assemble evaluation contexts for the EvaluationEngine."""

    def build(
        self,
        task: BaseTask,
        agent_result: AgentResult,
        *,
        trial_index: int | None = None,
        seed: int = 42,
        peer_results: list[AgentResult] | None = None,
        peer_evaluations: list[EvaluationResult] | None = None,
        experiment_id: str | None = None,
        run_id: str | None = None,
        run_metadata: dict[str, Any] | None = None,
        provider_metadata: dict[str, Any] | None = None,
    ) -> MetricContext:
        """Map a task + agent result into a MetricContext."""

        idx = trial_index if trial_index is not None else agent_result.trial_index
        gold = None
        if task.gold_answers:
            gold = task.gold_answers[0]
        elif task.gold_answer is not None:
            gold = task.gold_answer

        snapshot = TaskSnapshot(
            id=task.id,
            category=task.category.value if task.category else None,
            title=task.title,
            description=task.description,
            prompt=task.input.prompt,
            files=list(task.input.files),
            language=task.language,
            tags=list(task.tags),
            difficulty=task.difficulty.value if task.difficulty else None,
        )
        meta = {
            **(run_metadata or {}),
            "experiment_id": experiment_id,
            "run_id": run_id,
        }
        return MetricContext.from_agent_result(
            agent_result=agent_result,
            trial=TrialKey(
                task_id=task.id,
                agent_id=agent_result.agent_id,
                trial_index=idx,
                seed=seed,
            ),
            gold_answer=gold,
            alternate_gold_answers=list(task.alternate_gold_answers),
            expected_output=task.expected_output,
            expected_tool_calls=list(task.expected_tool_calls),
            failure_examples=list(task.failure_examples),
            task=snapshot,
            repository=task.repository,
            prompt=task.input.prompt,
            peer_results=peer_results or [],
            peer_evaluations=peer_evaluations or [],
            run_metadata=meta,
            provider_metadata=provider_metadata or {},
            repository_metadata=dict(task.repository.metadata) if task.repository else {},
            metadata={"task_version": task.task_version, "dataset_version": task.dataset_version},
        )
