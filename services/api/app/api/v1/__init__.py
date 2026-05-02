from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    agents,
    auth,
    health,
    missions,
    places,
    preferences,
    rankings,
    users,
    votes,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router, prefix="/users")
api_router.include_router(missions.router)

# C5-C: mission-scoped sub-resources (sec 7.4-7.7). Each router carries
# its own `/missions/{mission_id}/...` prefix so we mount them flat here.
api_router.include_router(preferences.router)
api_router.include_router(places.router)
api_router.include_router(rankings.router)
api_router.include_router(votes.router)
# C5-D: agents endpoints (sec 7.8) — list/detail/approve/reject for
# AgentRun rows, including HITL graph resume.
api_router.include_router(agents.router)

__all__ = ["api_router"]
