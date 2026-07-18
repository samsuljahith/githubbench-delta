"""Filesystem/JSONL result artifacts under an experiment directory."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from githubbench_delta.core.models import AgentResult, EvaluationResult
from githubbench_delta.pipeline.models import CachedEvaluation, WorkUnit
from githubbench_delta.storage.results.base import ResultStore


class JSONLResultStore(ResultStore):
    """Canonical on-disk artifacts: evaluation_results.json + trajectory.jsonl."""

    def __init__(self, experiment_dir: Path | str) -> None:
        self.root = Path(experiment_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.eval_path = self.root / "evaluation_results.json"
        self.traj_path = self.root / "trajectory.jsonl"
        self.cache_path = self.root / "eval_cache.jsonl"
        self.units_path = self.root / "completed_units.json"
        self._lock = threading.Lock()
        if not self.eval_path.is_file():
            self.eval_path.write_text("[]\n", encoding="utf-8")
        if not self.units_path.is_file():
            self.units_path.write_text("{}\n", encoding="utf-8")

    def save_evaluation(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        evaluation: EvaluationResult,
        agent_result: AgentResult | None = None,
    ) -> None:
        record = {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "unit_key": unit.key(),
            "task_id": unit.task_id,
            "agent_id": str(unit.agent_id),
            "trial_index": unit.trial_index,
            "evaluation": evaluation.model_dump(mode="json"),
        }
        if agent_result is not None:
            record["agent_result_summary"] = {
                "success": agent_result.success,
                "error": agent_result.error,
            }
        with self._lock:
            rows = self._read_json_list(self.eval_path)
            rows = [r for r in rows if r.get("unit_key") != unit.key()]
            rows.append(record)
            self.eval_path.write_text(
                json.dumps(rows, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    def save_trajectory(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
        agent_result: AgentResult,
    ) -> None:
        line = {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "unit_key": unit.key(),
            "task_id": unit.task_id,
            "agent_id": str(unit.agent_id),
            "trial_index": unit.trial_index,
            "agent_result": agent_result.model_dump(mode="json"),
            "trajectory": (
                agent_result.trajectory.model_dump(mode="json") if agent_result.trajectory else None
            ),
        }
        with self._lock, self.traj_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")

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
            data = self._read_json_dict(self.units_path)
            data[unit.key()] = {
                "experiment_id": experiment_id,
                "run_id": run_id,
                "success": success,
                "error": error,
            }
            self.units_path.write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    def is_unit_complete(
        self,
        *,
        experiment_id: str,
        run_id: str,
        unit: WorkUnit,
    ) -> bool:
        data = self._read_json_dict(self.units_path)
        entry = data.get(unit.key())
        return bool(entry and entry.get("success"))

    def list_evaluations(
        self,
        *,
        experiment_id: str,
        run_id: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = self._read_json_list(self.eval_path)
        out = [r for r in rows if r.get("experiment_id") == experiment_id]
        if run_id is not None:
            out = [r for r in out if r.get("run_id") == run_id]
        return out

    def get_cache_entry(self, cache_key: str) -> CachedEvaluation | None:
        if not self.cache_path.is_file():
            return None
        with self.cache_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get("cache_key") == cache_key:
                    return CachedEvaluation.model_validate(data)
        return None

    def put_cache_entry(self, entry: CachedEvaluation) -> None:
        with self._lock, self.cache_path.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json() + "\n")

    def load_agent_result(self, unit: WorkUnit) -> AgentResult | None:
        """Best-effort load of a stored agent result for resume/peer passes."""

        if not self.traj_path.is_file():
            return None
        with self.traj_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if data.get("unit_key") == unit.key() and data.get("agent_result"):
                    return AgentResult.model_validate(data["agent_result"])
        return None

    @staticmethod
    def _read_json_list(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding="utf-8") or "[]")
        return data if isinstance(data, list) else []

    @staticmethod
    def _read_json_dict(path: Path) -> dict[str, Any]:
        if not path.is_file():
            return {}
        data = json.loads(path.read_text(encoding="utf-8") or "{}")
        return data if isinstance(data, dict) else {}
