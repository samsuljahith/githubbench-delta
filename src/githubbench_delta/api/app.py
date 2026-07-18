"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from githubbench_delta import __version__
from githubbench_delta.core.config import clear_config_cache, load_config
from githubbench_delta.dashboard.api import api_router as dashboard_api_router
from githubbench_delta.dashboard.router import mount_dashboard_static
from githubbench_delta.dashboard.router import router as dashboard_router
from githubbench_delta.metrics.registry import catalog_entries


def create_app() -> FastAPI:
    """Create and configure the GitHubBench-Delta API application."""

    app = FastAPI(
        title="GitHubBench-Delta",
        description=(
            "Production evaluation framework for comparing AI coding agents "
            "on GitHub engineering tasks."
        ),
        version=__version__,
    )
    app.include_router(dashboard_router)
    app.include_router(dashboard_api_router)
    mount_dashboard_static(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/metrics/catalog")
    def metrics_catalog() -> list[dict[str, object]]:
        """Return the 18 GitHubBench-Delta methodology evaluators."""

        clear_config_cache()
        config = load_config()
        return catalog_entries(config)

    return app
