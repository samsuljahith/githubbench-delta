"""FastAPI application factory."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from githubbench_delta import __version__
from githubbench_delta.api.cases import cases_router
from githubbench_delta.api.facade import facade_router
from githubbench_delta.core.config import clear_config_cache, load_config
from githubbench_delta.dashboard.api import api_router as dashboard_api_router
from githubbench_delta.dashboard.router import mount_dashboard_static
from githubbench_delta.dashboard.router import router as dashboard_router
from githubbench_delta.healthcare_evaluation.api import healthcare_router
from githubbench_delta.metrics.registry import catalog_entries


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "GITHUBBENCH_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


# Lovable/Vite may bind arbitrary localhost ports (often 8080).
_CORS_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1):\d+"


def create_app() -> FastAPI:
    """Create and configure the GitHubBench-Delta API application."""

    # Ensure .env secrets are available via os.environ (uvicorn does not load .env).
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=".env", override=False)
    except Exception:
        pass

    app = FastAPI(
        title="GitHubBench-Delta",
        description=(
            "Production evaluation framework for comparing AI coding agents "
            "on GitHub engineering tasks."
        ),
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_origin_regex=_CORS_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(dashboard_router)
    app.include_router(dashboard_api_router)
    app.include_router(facade_router)
    app.include_router(cases_router)
    app.include_router(healthcare_router)
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
