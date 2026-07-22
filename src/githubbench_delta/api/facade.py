"""Thin REST facade for the ElderWise React frontend.

Wraps ExperimentRepository + MemorizationEngine only — no duplicated evaluator
logic and no fabricated scores. Empty artifacts → insufficient_data.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from githubbench_delta.core.config import load_config
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.memorization.engine import MemorizationEngine
from githubbench_delta.metrics.registry import catalog_entries

facade_router = APIRouter(tags=["facade"])

StatusLiteral = Literal["ok", "insufficient_data"]


def _default_experiment_id() -> str:
    return os.environ.get("GITHUBBENCH_DEFAULT_EXPERIMENT", "exp_6afa2ce533ba4e0a").strip()


def _repo() -> ExperimentRepository:
    return ExperimentRepository()


class FacadeEnvelope(BaseModel):
    ok: bool
    status: StatusLiteral
    experiment_id: str | None = None
    detail: str | None = None
    data: dict[str, Any] | None = None


class ExperimentRequest(BaseModel):
    experiment_id: str | None = None
    agent_id: str | None = None


class MemorizationRequest(BaseModel):
    experiment_ids: list[str] = Field(default_factory=list)
    experiment_id: str | None = None
    twins_path: str | None = None


def _resolve_experiment_id(raw: str | None) -> str:
    return (raw or _default_experiment_id()).strip()


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    agent_id: str | None,
) -> list[dict[str, Any]]:
    if not agent_id:
        return rows
    return [r for r in rows if str(r.get("agent_id", "")) == agent_id]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _flag_for_ratio(ratio: float) -> str:
    if ratio >= 0.7:
        return "normal"
    if ratio >= 0.4:
        return "watch"
    return "concern"


def _metric_label_map() -> dict[str, str]:
    try:
        entries = catalog_entries(load_config())
    except Exception:
        return {}
    out: dict[str, str] = {}
    for e in entries:
        mid = str(e.get("id") or e.get("metric_id") or "")
        label = str(e.get("name") or e.get("label") or mid)
        if mid:
            out[mid] = label
    return out


def _insufficient(experiment_id: str, detail: str) -> FacadeEnvelope:
    return FacadeEnvelope(
        ok=False,
        status="insufficient_data",
        experiment_id=experiment_id,
        detail=detail,
        data=None,
    )


@facade_router.post("/assessment", response_model=FacadeEnvelope)
def post_assessment(body: ExperimentRequest) -> FacadeEnvelope:
    """Map real evaluation group_scores into assessment-style domains."""

    experiment_id = _resolve_experiment_id(body.experiment_id)
    repo = _repo()
    rows = _filter_rows(repo.load_evaluations_raw(experiment_id), agent_id=body.agent_id)
    if not rows:
        return _insufficient(experiment_id, "No evaluation rows for experiment")

    # Average group_scores across matching rows
    group_accum: dict[str, list[float]] = {}
    agents: set[str] = set()
    for row in rows:
        agents.add(str(row.get("agent_id", "")))
        evaluation = row.get("evaluation") or {}
        groups = evaluation.get("group_scores") or {}
        if not isinstance(groups, dict):
            continue
        for name, val in groups.items():
            if isinstance(val, (int, float)):
                group_accum.setdefault(str(name), []).append(float(val))

    if not group_accum:
        return _insufficient(experiment_id, "No group_scores in evaluation rows")

    domains: list[dict[str, Any]] = []
    for name in sorted(group_accum):
        mean_v = _mean(group_accum[name])
        assert mean_v is not None
        score = round(mean_v * 5, 2)
        flag = _flag_for_ratio(mean_v)
        domains.append(
            {
                "domain": name.replace("_", " ").title(),
                "score": score,
                "max": 5,
                "flag": flag,
                "note": f"Mean group score {mean_v:.3f} from {len(group_accum[name])} rows",
            }
        )

    manifest = repo.load_experiment_manifest(experiment_id) or {}
    subject = {
        "id": experiment_id,
        "name": ", ".join(sorted(a for a in agents if a)) or "unknown",
        "agents": sorted(a for a in agents if a),
        "title": manifest.get("name") or manifest.get("title") or experiment_id,
        "synthetic": False,
        "source": "evaluation_results.group_scores",
    }

    return FacadeEnvelope(
        ok=True,
        status="ok",
        experiment_id=experiment_id,
        data={
            "domains": domains,
            "subject": subject,
            "method": "equal-weight mean of evaluation.group_scores scaled to 0–5",
        },
    )


@facade_router.post("/evaluate", response_model=FacadeEnvelope)
def post_evaluate(body: ExperimentRequest) -> FacadeEnvelope:
    """Return real per-metric averages shaped for the ElderWise EvalMetric UI."""

    experiment_id = _resolve_experiment_id(body.experiment_id)
    repo = _repo()
    rows = _filter_rows(repo.load_evaluations_raw(experiment_id), agent_id=body.agent_id)
    if not rows:
        return _insufficient(experiment_id, "No evaluation rows for experiment")

    labels = _metric_label_map()
    metric_accum: dict[str, list[float]] = {}
    for row in rows:
        evaluation = row.get("evaluation") or {}
        weighted = evaluation.get("metadata", {}).get("weighted_scores") or []
        if isinstance(weighted, list):
            for item in weighted:
                if not isinstance(item, dict):
                    continue
                mid = str(item.get("metric_id") or "")
                score = item.get("score")
                if mid and isinstance(score, (int, float)) and not item.get("skipped"):
                    metric_accum.setdefault(mid, []).append(float(score))

    if not metric_accum:
        for row in rows:
            evaluation = row.get("evaluation") or {}
            groups = evaluation.get("group_scores") or {}
            if isinstance(groups, dict):
                for name, val in groups.items():
                    if isinstance(val, (int, float)):
                        metric_accum.setdefault(str(name), []).append(float(val))

    if not metric_accum:
        return _insufficient(experiment_id, "No metric scores in evaluation rows")

    metrics: list[dict[str, Any]] = []
    for key in sorted(metric_accum):
        mean_v = _mean(metric_accum[key])
        assert mean_v is not None
        # Scores are 0–1 → report as %
        value = round(mean_v * 100, 2)
        metrics.append(
            {
                "key": key,
                "label": labels.get(key, key.replace("_", " ").title()),
                "value": value,
                "target": 70.0,
                "unit": "%",
                "description": f"Mean metric score from {len(metric_accum[key])} evaluation rows",
            }
        )

    return FacadeEnvelope(
        ok=True,
        status="ok",
        experiment_id=experiment_id,
        data={
            "metrics": metrics,
            "n_rows": len(rows),
            "agent_id": body.agent_id,
            "source": "evaluation_results",
        },
    )


@facade_router.post("/trust", response_model=FacadeEnvelope)
def post_trust(body: ExperimentRequest) -> FacadeEnvelope:
    """Equal-weight composite of group_scores (0–100). Documented formula; no fabrication."""

    experiment_id = _resolve_experiment_id(body.experiment_id)
    repo = _repo()
    rows = _filter_rows(repo.load_evaluations_raw(experiment_id), agent_id=body.agent_id)
    if not rows:
        return _insufficient(experiment_id, "No evaluation rows for experiment")

    group_accum: dict[str, list[float]] = {}
    for row in rows:
        evaluation = row.get("evaluation") or {}
        groups = evaluation.get("group_scores") or {}
        if not isinstance(groups, dict):
            continue
        for name, val in groups.items():
            if isinstance(val, (int, float)):
                group_accum.setdefault(str(name), []).append(float(val))

    if not group_accum:
        return _insufficient(experiment_id, "No group_scores for trust composite")

    breakdown: list[dict[str, Any]] = []
    means: list[float] = []
    for name in sorted(group_accum):
        m = _mean(group_accum[name])
        assert m is not None
        means.append(m)
        breakdown.append(
            {
                "name": name.replace("_", " ").title(),
                "value": round(m * 100, 1),
            }
        )

    overall = round((_mean(means) or 0.0) * 100, 1)
    if overall >= 75:
        band = "Trusted with clinician oversight"
    elif overall >= 50:
        band = "Assistive with review"
    else:
        band = "Not clinically usable"

    return FacadeEnvelope(
        ok=True,
        status="ok",
        experiment_id=experiment_id,
        data={
            "overall": overall,
            "band": band,
            "breakdown": breakdown,
            "method": "equal-weight mean of evaluation.group_scores × 100",
            "n_rows": len(rows),
            "agent_id": body.agent_id,
        },
    )


@facade_router.post("/memorization", response_model=FacadeEnvelope)
def post_memorization(body: MemorizationRequest) -> FacadeEnvelope:
    """Run MemorizationEngine on existing experiment artifacts."""

    ids = list(body.experiment_ids)
    if body.experiment_id:
        ids.append(body.experiment_id)
    if not ids:
        ids = [_default_experiment_id()]
    # dedupe preserve order
    seen: set[str] = set()
    experiment_ids = []
    for i in ids:
        if i and i not in seen:
            seen.add(i)
            experiment_ids.append(i)

    engine = MemorizationEngine()
    twins_path = Path(body.twins_path) if body.twins_path else None
    try:
        report = engine.analyze(experiment_ids, twins_path=twins_path)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    payload = report.model_dump(mode="json")
    if not report.breakdowns and not report.lifts:
        return FacadeEnvelope(
            ok=False,
            status="insufficient_data",
            experiment_id=experiment_ids[0] if experiment_ids else None,
            detail="MemorizationEngine produced no lifts/breakdowns",
            data=payload,
        )

    return FacadeEnvelope(
        ok=True,
        status="ok",
        experiment_id=experiment_ids[0] if len(experiment_ids) == 1 else None,
        data=payload,
    )
