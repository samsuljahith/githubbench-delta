"""Read-only experiment artifact repository for the dashboard."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from githubbench_delta import __version__
from githubbench_delta.core.config import AppConfig, load_config
from githubbench_delta.dashboard.schemas import (
    EvaluationRow,
    ExperimentDetail,
    ExperimentSummary,
    SettingsSnapshot,
    TrajectoryDetail,
    TrajectoryIndexItem,
)


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _paginate(
    rows: list[Any],
    *,
    page: int,
    page_size: int,
) -> tuple[list[Any], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 500))
    total = len(rows)
    start = (page - 1) * page_size
    return rows[start : start + page_size], total


def _sort_rows(
    rows: list[dict[str, Any]],
    *,
    sort: str | None,
    order: str,
) -> list[dict[str, Any]]:
    if not sort:
        return rows
    reverse = order.lower() != "asc"

    def key(row: dict[str, Any]) -> Any:
        val = row.get(sort)
        return (val is None, val)

    try:
        return sorted(rows, key=key, reverse=reverse)
    except TypeError:
        return rows


class ExperimentRepository:
    """Filesystem-first reader of Phase 5 experiment artifacts."""

    def __init__(
        self,
        *,
        results_dir: Path | str | None = None,
        sqlite_path: Path | str | None = None,
        app_config: AppConfig | None = None,
    ) -> None:
        self.app_config = app_config or load_config()
        self.results_dir = Path(results_dir or self.app_config.runtime.pipeline.results_dir)
        self.sqlite_path = Path(sqlite_path or self.app_config.runtime.storage.sqlite_path)
        self._task_meta_cache: dict[str, dict[str, Any]] = {}

    def list_experiment_ids(self) -> list[str]:
        if not self.results_dir.is_dir():
            return []
        ids: list[str] = []
        for child in sorted(self.results_dir.iterdir()):
            if child.is_dir() and (child / "experiment.json").is_file():
                ids.append(child.name)
        return ids

    def experiment_dir(self, experiment_id: str) -> Path:
        return self.results_dir / experiment_id

    def _read_json(self, path: Path) -> Any:
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def load_experiment_manifest(self, experiment_id: str) -> dict[str, Any] | None:
        data = self._read_json(self.experiment_dir(experiment_id) / "experiment.json")
        return data if isinstance(data, dict) else None

    def load_run_manifest(self, experiment_id: str) -> dict[str, Any] | None:
        data = self._read_json(self.experiment_dir(experiment_id) / "run.json")
        return data if isinstance(data, dict) else None

    def load_evaluations_raw(self, experiment_id: str) -> list[dict[str, Any]]:
        path = self.experiment_dir(experiment_id) / "evaluation_results.json"
        data = self._read_json(path)
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        # Fallback: SQLite
        return self._sqlite_evaluations(experiment_id)

    def _sqlite_evaluations(self, experiment_id: str) -> list[dict[str, Any]]:
        if not self.sqlite_path.is_file():
            return []
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            rows = conn.execute(
                "SELECT payload FROM evaluations WHERE experiment_id=?",
                (experiment_id,),
            ).fetchall()
            conn.close()
            return [json.loads(r[0]) for r in rows]
        except sqlite3.Error:
            return []

    def evaluation_rows(self, experiment_id: str) -> list[EvaluationRow]:
        out: list[EvaluationRow] = []
        for raw in self.load_evaluations_raw(experiment_id):
            ev = raw.get("evaluation") or {}
            metrics = ev.get("metric_results") or {}
            metric_scores = {
                mid: float(m.get("score", 0.0))
                for mid, m in metrics.items()
                if isinstance(m, dict) and not m.get("skipped")
            }
            summary = raw.get("agent_result_summary") or {}
            meta = ev.get("metadata") or {}
            out.append(
                EvaluationRow(
                    experiment_id=raw.get("experiment_id", experiment_id),
                    run_id=raw.get("run_id", ""),
                    unit_key=raw.get("unit_key", ""),
                    task_id=raw.get("task_id", ""),
                    agent_id=str(raw.get("agent_id", "")),
                    trial_index=int(raw.get("trial_index", 0)),
                    overall_score=ev.get("overall_score"),
                    confidence_score=ev.get("confidence_score"),
                    group_scores={k: float(v) for k, v in (ev.get("group_scores") or {}).items()},
                    success=summary.get("success"),
                    category=meta.get("category"),
                    metric_scores=metric_scores,
                    latency_ms=None,
                    cost_usd=None,
                )
            )
        # Enrich latency/cost from trajectories when available
        traj_index = {t["unit_key"]: t for t in self._load_trajectory_raw(experiment_id)}
        enriched: list[EvaluationRow] = []
        for row in out:
            t = traj_index.get(row.unit_key)
            if t and isinstance(t.get("agent_result"), dict):
                metrics = t["agent_result"].get("metrics") or {}
                enriched.append(
                    row.model_copy(
                        update={
                            "latency_ms": metrics.get("latency_ms"),
                            "cost_usd": metrics.get("estimated_cost_usd"),
                            "success": (
                                row.success
                                if row.success is not None
                                else t["agent_result"].get("success")
                            ),
                        }
                    )
                )
            else:
                enriched.append(row)
        return enriched

    def _load_trajectory_raw(self, experiment_id: str) -> list[dict[str, Any]]:
        path = self.experiment_dir(experiment_id) / "trajectory.jsonl"
        if not path.is_file():
            return []
        rows: list[dict[str, Any]] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def list_experiments(
        self,
        *,
        status: str | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 50,
        sort: str | None = "updated_at",
        order: str = "desc",
    ) -> tuple[list[ExperimentSummary], int]:
        summaries: list[ExperimentSummary] = []
        for eid in self.list_experiment_ids():
            manifest = self.load_experiment_manifest(eid)
            if not manifest:
                continue
            if status and manifest.get("status") != status:
                continue
            if q:
                blob = json.dumps(manifest).lower()
                if q.lower() not in blob:
                    continue
            run = self.load_run_manifest(eid) or {}
            scores = [
                r.overall_score for r in self.evaluation_rows(eid) if r.overall_score is not None
            ]
            summaries.append(
                ExperimentSummary(
                    experiment_id=eid,
                    name=str(manifest.get("name") or ""),
                    status=str(manifest.get("status") or ""),
                    seed=int(manifest.get("seed") or 42),
                    trial_count=int(manifest.get("trial_count") or 1),
                    agent_ids=list(manifest.get("agent_ids") or []),
                    task_ids=list(manifest.get("task_ids") or []),
                    dataset_path=str(manifest.get("dataset_path") or ""),
                    created_at=manifest.get("created_at"),
                    updated_at=manifest.get("updated_at"),
                    units_done=int(run.get("units_done") or 0),
                    units_total=int(run.get("units_total") or 0),
                    mean_overall_score=_mean([float(s) for s in scores]),
                )
            )
        as_dicts = [s.model_dump() for s in summaries]
        as_dicts = _sort_rows(as_dicts, sort=sort, order=order)
        page_items, total = _paginate(as_dicts, page=page, page_size=page_size)
        return [ExperimentSummary.model_validate(x) for x in page_items], total

    def get_experiment(self, experiment_id: str) -> ExperimentDetail | None:
        manifest = self.load_experiment_manifest(experiment_id)
        if not manifest:
            return None
        run = self.load_run_manifest(experiment_id)
        rows = self.evaluation_rows(experiment_id)
        scores = [r.overall_score for r in rows if r.overall_score is not None]
        exp_dir = self.experiment_dir(experiment_id)
        artifacts = sorted(p.name for p in exp_dir.iterdir() if p.is_file())
        return ExperimentDetail(
            experiment=manifest,
            run=run,
            summary={
                "evaluation_count": len(rows),
                "mean_overall_score": _mean([float(s) for s in scores]),
                "agents": sorted({r.agent_id for r in rows}),
                "tasks": sorted({r.task_id for r in rows}),
            },
            artifacts=artifacts,
        )

    def list_evaluations(
        self,
        experiment_id: str,
        *,
        agent_id: str | None = None,
        task_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
        sort: str | None = "overall_score",
        order: str = "desc",
    ) -> tuple[list[EvaluationRow], int]:
        rows = self.evaluation_rows(experiment_id)
        if agent_id:
            rows = [r for r in rows if r.agent_id == agent_id]
        if task_id:
            rows = [r for r in rows if r.task_id == task_id]
        as_dicts = [r.model_dump() for r in rows]
        as_dicts = _sort_rows(as_dicts, sort=sort, order=order)
        page_items, total = _paginate(as_dicts, page=page, page_size=page_size)
        return [EvaluationRow.model_validate(x) for x in page_items], total

    def list_trajectories(self, experiment_id: str) -> list[TrajectoryIndexItem]:
        items: list[TrajectoryIndexItem] = []
        for raw in self._load_trajectory_raw(experiment_id):
            ar = raw.get("agent_result") or {}
            traj = raw.get("trajectory") or ar.get("trajectory") or {}
            steps = traj.get("steps") if isinstance(traj, dict) else []
            items.append(
                TrajectoryIndexItem(
                    unit_key=str(raw.get("unit_key") or ""),
                    task_id=str(raw.get("task_id") or ""),
                    agent_id=str(raw.get("agent_id") or ""),
                    trial_index=int(raw.get("trial_index") or 0),
                    success=ar.get("success"),
                    step_count=len(steps or []),
                )
            )
        return items

    def get_trajectory(self, experiment_id: str, unit_key: str) -> TrajectoryDetail | None:
        for raw in self._load_trajectory_raw(experiment_id):
            if raw.get("unit_key") != unit_key:
                continue
            ar = raw.get("agent_result") or {}
            traj = raw.get("trajectory") or ar.get("trajectory") or {}
            steps = list((traj or {}).get("steps") or [])
            tool_calls: list[dict[str, Any]] = []
            warnings: list[str] = []
            for step in steps:
                if step.get("tool_call"):
                    tool_calls.append(step["tool_call"])
                if step.get("error"):
                    warnings.append(str(step["error"]))
                meta = step.get("metadata") or {}
                if meta.get("warning"):
                    warnings.append(str(meta["warning"]))
            output = (ar.get("output") or {}).get("content") or ""
            retries = int((ar.get("metadata") or {}).get("retries") or 0)
            plan = ""
            for step in steps:
                if step.get("kind") in {"plan", "assistant"} and step.get("content"):
                    plan = str(step["content"])
                    break
            return TrajectoryDetail(
                unit_key=unit_key,
                task_id=str(raw.get("task_id") or ""),
                agent_id=str(raw.get("agent_id") or ""),
                trial_index=int(raw.get("trial_index") or 0),
                success=ar.get("success"),
                final_output=str(output),
                error=ar.get("error"),
                steps=steps,
                tool_calls=tool_calls,
                warnings=warnings,
                retries=retries,
                plan=plan,
            )
        return None

    def load_task_metadata(self, dataset_path: str | Path) -> dict[str, dict[str, Any]]:
        """Read-only enrichment from dataset tasks.jsonl if present."""

        key = str(dataset_path)
        if key in self._task_meta_cache:
            return self._task_meta_cache[key]
        root = Path(dataset_path)
        tasks_file = root / "tasks.jsonl"
        meta: dict[str, dict[str, Any]] = {}
        if tasks_file.is_file():
            with tasks_file.open(encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    tid = rec.get("id")
                    if not tid:
                        continue
                    repo = rec.get("repository") or {}
                    meta[str(tid)] = {
                        "category": rec.get("category"),
                        "difficulty": rec.get("difficulty"),
                        "language": rec.get("language"),
                        "repository": repo.get("url") or repo.get("local_path"),
                    }
        self._task_meta_cache[key] = meta
        return meta

    def settings_snapshot(self) -> SettingsSnapshot:
        return SettingsSnapshot(
            results_dir=str(self.results_dir),
            sqlite_path=str(self.sqlite_path),
            dataset_default="datasets/v1",
            version=__version__,
            auth_enabled=False,
            websocket_enabled=False,
        )

    def all_evaluation_rows(self, experiment_ids: list[str] | None = None) -> list[EvaluationRow]:
        ids = experiment_ids or self.list_experiment_ids()
        rows: list[EvaluationRow] = []
        for eid in ids:
            rows.extend(self.evaluation_rows(eid))
        return rows
