"""ResultStore protocol for evaluation artifacts and resume/cache."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from githubbench_delta.core.models import AgentResult, EvaluationResult
from githubbench_delta.pipeline.models import CachedEvaluation, WorkUnit


class ResultStore(ABC):
    """Persist evaluations, trajectories, work-unit completion, and cache."""

    @abstractmethod
    def save_evaluation(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        evaluation: EvaluationResult,
        agent_result: AgentResult | None = None,
    ) -> None:
        """Persist one evaluation result."""

    @abstractmethod
    def save_trajectory(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        agent_result: AgentResult,
    ) -> None:
        """Append one trajectory / agent-result line."""

    @abstractmethod
    def mark_unit_complete(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        """Record that a work unit finished."""

    @abstractmethod
    def is_unit_complete(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
    ) -> bool:
        """Return True if the work unit already completed successfully."""

    @abstractmethod
    def list_evaluations(
        self,
        *,
        experiment_id: str,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List stored evaluation payloads for an experiment."""

    @abstractmethod
    def get_cache_entry(self, cache_key: str) -> CachedEvaluation | None:
        """Lookup a cached evaluation by key."""

    @abstractmethod
    def put_cache_entry(self, entry: CachedEvaluation) -> None:
        """Store a cached evaluation entry."""

    def close(self) -> None:  # noqa: B027 — optional hook, default no-op
        """Release resources (optional)."""
        return

    def __enter__(self) -> ResultStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
