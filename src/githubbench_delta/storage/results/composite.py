"""Dual-write ResultStore: JSONL artifacts + SQLite index."""

from __future__ import annotations

from typing import Any

from githubbench_delta.core.models import AgentResult, EvaluationResult
from githubbench_delta.pipeline.models import CachedEvaluation, WorkUnit
from githubbench_delta.storage.results.base import ResultStore
from githubbench_delta.storage.results.jsonl_store import JSONLResultStore
from githubbench_delta.storage.results.sqlite_store import SQLiteResultStore


class CompositeResultStore(ResultStore):
    """Canonical JSONL artifacts with SQLite for resume/query/cache."""

    def __init__(self, jsonl: JSONLResultStore, sqlite: SQLiteResultStore) -> None:
        self.jsonl = jsonl
        self.sqlite = sqlite

    def save_evaluation(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        evaluation: EvaluationResult,
        agent_result: AgentResult | None = None,
    ) -> None:
        self.jsonl.save_evaluation(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            evaluation=evaluation,
            agent_result=agent_result,
        )
        self.sqlite.save_evaluation(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            evaluation=evaluation,
            agent_result=agent_result,
        )

    def save_trajectory(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        agent_result: AgentResult,
    ) -> None:
        self.jsonl.save_trajectory(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            agent_result=agent_result,
        )
        self.sqlite.save_trajectory(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            agent_result=agent_result,
        )

    def mark_unit_complete(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        self.jsonl.mark_unit_complete(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            success=success,
            error=error,
        )
        self.sqlite.mark_unit_complete(
            experiment_id=experiment_id,
            run_id=run_id,
            unit=unit,
            success=success,
            error=error,
        )

    def is_unit_complete(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
    ) -> bool:
        # Prefer SQLite; fall back to JSONL units file.
        if self.sqlite.is_unit_complete(experiment_id=experiment_id, run_id=run_id, unit=unit):
            return True
        return self.jsonl.is_unit_complete(experiment_id=experiment_id, run_id=run_id, unit=unit)

    def list_evaluations(
        self,
        *,
        experiment_id: str,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self.sqlite.list_evaluations(experiment_id=experiment_id, run_id=run_id)
        if rows:
            return rows
        return self.jsonl.list_evaluations(experiment_id=experiment_id, run_id=run_id)

    def get_cache_entry(self, cache_key: str) -> CachedEvaluation | None:
        entry = self.sqlite.get_cache_entry(cache_key)
        if entry is not None:
            return entry
        return self.jsonl.get_cache_entry(cache_key)

    def put_cache_entry(self, entry: CachedEvaluation) -> None:
        self.sqlite.put_cache_entry(entry)
        self.jsonl.put_cache_entry(entry)

    def load_agent_result(self, unit: WorkUnit) -> AgentResult | None:
        return self.jsonl.load_agent_result(unit)

    def close(self) -> None:
        self.sqlite.close()
