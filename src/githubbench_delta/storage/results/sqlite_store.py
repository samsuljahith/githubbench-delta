"""SQLite ResultStore for resume, query, and evaluation cache."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from githubbench_delta.core.models import AgentResult, EvaluationResult
from githubbench_delta.pipeline.models import CachedEvaluation, WorkUnit
from githubbench_delta.storage.results.base import ResultStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
  experiment_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  experiment_id TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS work_units (
  experiment_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  unit_key TEXT NOT NULL,
  success INTEGER NOT NULL,
  error TEXT,
  PRIMARY KEY (experiment_id, run_id, unit_key)
);
CREATE TABLE IF NOT EXISTS evaluations (
  experiment_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  unit_key TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (experiment_id, run_id, unit_key)
);
CREATE TABLE IF NOT EXISTS eval_cache (
  cache_key TEXT PRIMARY KEY,
  payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trajectories (
  experiment_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  unit_key TEXT NOT NULL,
  payload TEXT NOT NULL,
  PRIMARY KEY (experiment_id, run_id, unit_key)
);
"""


class SQLiteResultStore(ResultStore):
    """OLTP persistence for evaluations and work-unit completion."""

    def __init__(self, db_path: Path | str) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def save_evaluation(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        evaluation: EvaluationResult,
        agent_result: AgentResult | None = None,
    ) -> None:
        payload = {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "unit_key": unit.key(),
            "task_id": unit.task_id,
            "agent_id": str(unit.agent_id),
            "trial_index": unit.trial_index,
            "evaluation": evaluation.model_dump(mode="json"),
        }
        if agent_result is not None:
            payload["agent_result_summary"] = {
                "success": agent_result.success,
                "error": agent_result.error,
            }
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO evaluations(experiment_id, run_id, unit_key, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(experiment_id, run_id, unit_key)
                DO UPDATE SET payload=excluded.payload
                """,
                (experiment_id, run_id, unit.key(), json.dumps(payload)),
            )
            self._conn.commit()

    def save_trajectory(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        agent_result: AgentResult,
    ) -> None:
        payload = {
            "agent_result": agent_result.model_dump(mode="json"),
            "trajectory": (
                agent_result.trajectory.model_dump(mode="json") if agent_result.trajectory else None
            ),
        }
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO trajectories(experiment_id, run_id, unit_key, payload)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(experiment_id, run_id, unit_key)
                DO UPDATE SET payload=excluded.payload
                """,
                (experiment_id, run_id, unit.key(), json.dumps(payload)),
            )
            self._conn.commit()

    def mark_unit_complete(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO work_units(experiment_id, run_id, unit_key, success, error)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(experiment_id, run_id, unit_key)
                DO UPDATE SET success=excluded.success, error=excluded.error
                """,
                (experiment_id, run_id, unit.key(), 1 if success else 0, error),
            )
            self._conn.commit()

    def is_unit_complete(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
    ) -> bool:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT success FROM work_units
                WHERE experiment_id=? AND run_id=? AND unit_key=?
                """,
                (experiment_id, run_id, unit.key()),
            ).fetchone()
        return bool(row and row[0] == 1)

    def list_evaluations(
        self,
        *,
        experiment_id: str,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            if run_id is None:
                rows = self._conn.execute(
                    "SELECT payload FROM evaluations WHERE experiment_id=?",
                    (experiment_id,),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT payload FROM evaluations
                    WHERE experiment_id=? AND run_id=?
                    """,
                    (experiment_id, run_id),
                ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get_cache_entry(self, cache_key: str) -> CachedEvaluation | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM eval_cache WHERE cache_key=?",
                (cache_key,),
            ).fetchone()
        if not row:
            return None
        return CachedEvaluation.model_validate(json.loads(row[0]))

    def put_cache_entry(self, entry: CachedEvaluation) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO eval_cache(cache_key, payload)
                VALUES (?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET payload=excluded.payload
                """,
                (entry.cache_key, entry.model_dump_json()),
            )
            self._conn.commit()

    def save_experiment_payload(self, experiment_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO experiments(experiment_id, payload) VALUES (?, ?)
                ON CONFLICT(experiment_id) DO UPDATE SET payload=excluded.payload
                """,
                (experiment_id, json.dumps(payload)),
            )
            self._conn.commit()

    def save_run_payload(self, run_id: str, experiment_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO runs(run_id, experiment_id, payload) VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET payload=excluded.payload
                """,
                (run_id, experiment_id, json.dumps(payload)),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()
