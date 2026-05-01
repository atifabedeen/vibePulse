from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Response

from app.api.v1 import api_router
from app.api.v1.health import health, ready
from app.config import Settings, get_settings
from app.database import dispose_engine
from app.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI application factory.

    Mounts:
      - /api/v1/*  : versioned API surface (currently only health endpoints)
      - /health    : liveness (also alias for k8s probe URL stability)
      - /ready     : readiness (DB + Redis)
      - /metrics   : Prometheus exposition (stub for now; M6 wires real metrics)
    """
    cfg = settings or get_settings()
    configure_logging(level=cfg.log_level, service=cfg.service_name, env=cfg.env)
    log = structlog.get_logger(__name__)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        log.info("api_startup", env=cfg.env, service=cfg.service_name)
        try:
            yield
        finally:
            log.info("api_shutdown")
            await dispose_engine()

    app = FastAPI(
        title="VibeBite API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Versioned router (currently health endpoints; future PRs add auth, missions, etc.)
    app.include_router(api_router, prefix="/api/v1")

    # Top-level convenience routes — k8s/ECS probes hit these without /api/v1.
    app.add_api_route("/health", health, methods=["GET"], tags=["health"])
    app.add_api_route("/ready", ready, methods=["GET"], tags=["health"])

    # Stub /metrics so Prometheus scrape config can target it from day one.
    # Real exposition is wired in M6 via prometheus_client.
    @app.get("/metrics", tags=["observability"])
    async def metrics() -> Response:
        body = (
            "# HELP vibebite_api_up 1 if the API process is alive.\n"
            "# TYPE vibebite_api_up gauge\n"
            "vibebite_api_up 1\n"
        )
        return Response(content=body, media_type="text/plain; version=0.0.4")

    return app


app = create_app()
