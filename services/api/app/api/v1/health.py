from __future__ import annotations

from typing import Any

import redis.asyncio as redis
import structlog
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.config import get_settings
from app.database import get_engine

router = APIRouter(tags=["health"])
log = structlog.get_logger(__name__)


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always 200 if the process is up."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, Any]:
    """Readiness probe — 200 only when DB and Redis are reachable.

    On any failure the response is 503 with which check failed. Kubernetes /
    ECS wire this to traffic gating; do not move heavy work into here.
    """
    checks: dict[str, str] = {"db": "unknown", "redis": "unknown"}
    ok = True

    # --- Postgres ---
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:  # noqa: BLE001
        log.warning("readiness_db_failed", error=str(exc))
        checks["db"] = f"error: {exc.__class__.__name__}"
        ok = False

    # --- Redis ---
    settings = get_settings()
    client: redis.Redis | None = None
    try:
        client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        pong = await client.ping()
        checks["redis"] = "ok" if pong else "no_pong"
        if not pong:
            ok = False
    except Exception as exc:  # noqa: BLE001
        log.warning("readiness_redis_failed", error=str(exc))
        checks["redis"] = f"error: {exc.__class__.__name__}"
        ok = False
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass

    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if ok else "degraded", "checks": checks}
