"""Dashboard HTML pages and health probe."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

DASHBOARD_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(DASHBOARD_DIR / "templates"))

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/health")
def dashboard_health() -> dict[str, str]:
    """Lightweight health probe for the dashboard subsystem."""

    return {"status": "ok", "component": "dashboard"}


@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/dashboard/", response_class=HTMLResponse)
async def page_overview(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "overview.html", {"active": "overview"})


@router.get("/dashboard/experiments", response_class=HTMLResponse)
async def page_experiments(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "experiments.html", {"active": "experiments"})


@router.get("/dashboard/experiments/{experiment_id}", response_class=HTMLResponse)
async def page_experiment_detail(request: Request, experiment_id: str) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request,
        "experiment_detail.html",
        {"active": "experiments", "experiment_id": experiment_id},
    )


@router.get("/dashboard/leaderboard", response_class=HTMLResponse)
async def page_leaderboard(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "leaderboard.html", {"active": "leaderboard"})


@router.get("/dashboard/agents", response_class=HTMLResponse)
async def page_agents(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "agents.html", {"active": "agents"})


@router.get("/dashboard/tasks", response_class=HTMLResponse)
async def page_tasks(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "tasks.html", {"active": "tasks"})


@router.get("/dashboard/metrics", response_class=HTMLResponse)
async def page_metrics(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "metrics.html", {"active": "metrics"})


@router.get("/dashboard/trajectories", response_class=HTMLResponse)
async def page_trajectories(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "trajectories.html", {"active": "trajectories"})


@router.get("/dashboard/settings", response_class=HTMLResponse)
async def page_settings(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "settings.html", {"active": "settings"})


def mount_dashboard_static(app) -> None:
    """Mount dashboard static assets on the FastAPI app."""

    static_dir = DASHBOARD_DIR / "static"
    app.mount(
        "/dashboard/static",
        StaticFiles(directory=str(static_dir)),
        name="dashboard-static",
    )
