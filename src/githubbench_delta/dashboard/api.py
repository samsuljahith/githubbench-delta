"""REST API for the evaluation dashboard (read-only)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from githubbench_delta.dashboard.aggregations import (
    build_agent_compare,
    build_correlation,
    build_leaderboard,
    build_metric_stats,
    build_overview,
    build_task_rows,
)
from githubbench_delta.dashboard.auth import get_current_principal
from githubbench_delta.dashboard.charts import CHART_BUILDERS, build_chart
from githubbench_delta.dashboard.export import export
from githubbench_delta.dashboard.repository import ExperimentRepository
from githubbench_delta.dashboard.schemas import (
    AgentCompareResponse,
    CorrelationResponse,
    EvaluationRow,
    ExperimentDetail,
    ExperimentSummary,
    LeaderboardRow,
    MetricStat,
    OverviewResponse,
    Page,
    Principal,
    SettingsSnapshot,
    TaskRow,
    TrajectoryDetail,
    TrajectoryIndexItem,
)

api_router = APIRouter(prefix="/dashboard/api", tags=["dashboard-api"])


def get_repository() -> ExperimentRepository:
    return ExperimentRepository()


RepoDep = Annotated[ExperimentRepository, Depends(get_repository)]
PrincipalDep = Annotated[Principal, Depends(get_current_principal)]


def _parse_ids(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [x.strip() for x in raw.split(",") if x.strip()]


@api_router.get("/overview", response_model=OverviewResponse)
def overview(repo: RepoDep, _principal: PrincipalDep) -> OverviewResponse:
    return build_overview(repo)


@api_router.get("/experiments", response_model=Page[ExperimentSummary])
def list_experiments(
    repo: RepoDep,
    _principal: PrincipalDep,
    status: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort: str | None = "updated_at",
    order: str = "desc",
) -> Page[ExperimentSummary]:
    items, total = repo.list_experiments(
        status=status, q=q, page=page, page_size=page_size, sort=sort, order=order
    )
    return Page(items=items, total=total, page=page, page_size=page_size, sort=sort, order=order)


@api_router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
def get_experiment(experiment_id: str, repo: RepoDep, _principal: PrincipalDep) -> ExperimentDetail:
    detail = repo.get_experiment(experiment_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return detail


@api_router.get(
    "/experiments/{experiment_id}/evaluations",
    response_model=Page[EvaluationRow],
)
def list_evaluations(
    experiment_id: str,
    repo: RepoDep,
    _principal: PrincipalDep,
    agent_id: str | None = None,
    task_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort: str | None = "overall_score",
    order: str = "desc",
) -> Page[EvaluationRow]:
    if repo.load_experiment_manifest(experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    items, total = repo.list_evaluations(
        experiment_id,
        agent_id=agent_id,
        task_id=task_id,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )
    return Page(items=items, total=total, page=page, page_size=page_size, sort=sort, order=order)


@api_router.get(
    "/experiments/{experiment_id}/trajectories",
    response_model=list[TrajectoryIndexItem],
)
def list_trajectories(
    experiment_id: str, repo: RepoDep, _principal: PrincipalDep
) -> list[TrajectoryIndexItem]:
    if repo.load_experiment_manifest(experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return repo.list_trajectories(experiment_id)


@api_router.get(
    "/experiments/{experiment_id}/trajectories/{unit_key:path}",
    response_model=TrajectoryDetail,
)
def get_trajectory(
    experiment_id: str,
    unit_key: str,
    repo: RepoDep,
    _principal: PrincipalDep,
) -> TrajectoryDetail:
    detail = repo.get_trajectory(experiment_id, unit_key)
    if detail is None:
        raise HTTPException(status_code=404, detail="Trajectory not found")
    return detail


@api_router.get("/leaderboard", response_model=Page[LeaderboardRow])
def leaderboard(
    repo: RepoDep,
    _principal: PrincipalDep,
    experiment_ids: str | None = None,
    agent_id: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort: str = "overall_score",
    order: str = "desc",
) -> Page[LeaderboardRow]:
    items, total = build_leaderboard(
        repo,
        experiment_ids=_parse_ids(experiment_ids),
        agent_id=agent_id,
        category=category,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )
    return Page(items=items, total=total, page=page, page_size=page_size, sort=sort, order=order)


@api_router.get("/agents/compare", response_model=AgentCompareResponse)
def agents_compare(
    repo: RepoDep,
    _principal: PrincipalDep,
    experiment_ids: str | None = None,
) -> AgentCompareResponse:
    return build_agent_compare(repo, experiment_ids=_parse_ids(experiment_ids))


@api_router.get("/tasks", response_model=Page[TaskRow])
def tasks(
    repo: RepoDep,
    _principal: PrincipalDep,
    experiment_ids: str | None = None,
    category: str | None = None,
    language: str | None = None,
    difficulty: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort: str = "mean_score",
    order: str = "desc",
) -> Page[TaskRow]:
    items, total = build_task_rows(
        repo,
        experiment_ids=_parse_ids(experiment_ids),
        category=category,
        language=language,
        difficulty=difficulty,
        q=q,
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
    )
    return Page(items=items, total=total, page=page, page_size=page_size, sort=sort, order=order)


@api_router.get("/metrics/summary", response_model=list[MetricStat])
def metrics_summary(
    repo: RepoDep,
    _principal: PrincipalDep,
    experiment_ids: str | None = None,
) -> list[MetricStat]:
    return build_metric_stats(repo, experiment_ids=_parse_ids(experiment_ids))


@api_router.get("/metrics/correlation", response_model=CorrelationResponse)
def metrics_correlation(
    repo: RepoDep,
    _principal: PrincipalDep,
    experiment_ids: str | None = None,
) -> CorrelationResponse:
    return build_correlation(repo, experiment_ids=_parse_ids(experiment_ids))


@api_router.get("/charts/{name}")
def charts(
    name: str,
    repo: RepoDep,
    _principal: PrincipalDep,
    experiment_ids: str | None = None,
    experiment_id: str | None = None,
    unit_key: str | None = None,
    metric_id: str = "task_resolution",
) -> dict[str, Any]:
    if name not in CHART_BUILDERS:
        raise HTTPException(status_code=404, detail=f"Unknown chart: {name}")
    kwargs: dict[str, Any] = {"experiment_ids": _parse_ids(experiment_ids)}
    if name == "histogram":
        kwargs["metric_id"] = metric_id
    if name == "timeline":
        if not experiment_id or not unit_key:
            raise HTTPException(
                status_code=400,
                detail="timeline requires experiment_id and unit_key",
            )
        kwargs = {"experiment_id": experiment_id, "unit_key": unit_key}
    try:
        return build_chart(name, repo, **kwargs)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.get("/export/{format}")
def export_data(
    format: str,
    repo: RepoDep,
    _principal: PrincipalDep,
    experiment_id: str | None = None,
) -> Response:
    try:
        media, body = export(format, repo, experiment_id=experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=body, media_type=media)


@api_router.get("/settings", response_model=SettingsSnapshot)
def settings(repo: RepoDep, _principal: PrincipalDep) -> SettingsSnapshot:
    return repo.settings_snapshot()


@api_router.get("/ws/status")
def websocket_status(_principal: PrincipalDep) -> dict[str, Any]:
    """Capability stub for future WebSocket streaming."""

    return {
        "websocket_enabled": False,
        "status": "not_implemented",
        "message": "WebSocket streaming is reserved for a future release.",
        "http_status_equivalent": 501,
    }
