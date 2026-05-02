from __future__ import annotations

"""`/api/v1/missions/{mission_id}/places` (sec 7.5).

* `GET  /`             — cached candidate places for this mission, derived
                         from the latest `agent_run`'s `rankings` rows.
                         Returns `[]` when the agent hasn't run yet.
* `GET  /{place_id}`   — full `PlaceDetail` (incl. raw Google blob).
* `POST /refresh`      — Owner-only. Kicks a fresh recommend graph run
                         (re-fetches Places, re-scores, etc.) in the
                         background and 202s with the new
                         ``agent_run_id`` so the client can poll.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.mission import MissionMember
from app.models.place import Place
from app.models.ranking import Ranking
from app.schemas.place import PlaceDetail, PlaceOut, PlaceRefreshOut
from app.security.deps import get_mission_member, get_mission_owner
from app.services import graph_service

router = APIRouter(
    prefix="/missions/{mission_id}/places",
    tags=["places"],
)


@router.get("/", response_model=List[PlaceOut])
async def list_places_for_mission(
    mission_id: str,
    _: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> List[Place]:
    """Cached Place rows for the mission, via its latest agent_run.

    We pick the most recent `rankings.created_at` for the mission, take
    its `agent_run_id`, then return every Place referenced by rankings
    of that run, ordered by `rank` ascending. If no rankings exist yet,
    return an empty list (not a 404 — the mobile client renders an empty
    state).
    """
    latest_run_id = (
        await session.execute(
            select(Ranking.agent_run_id)
            .where(Ranking.mission_id == mission_id)
            .order_by(Ranking.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_run_id is None:
        return []

    rows = (
        await session.execute(
            select(Place, Ranking.rank)
            .join(Ranking, Ranking.place_id == Place.id)
            .where(
                Ranking.mission_id == mission_id,
                Ranking.agent_run_id == latest_run_id,
            )
            .order_by(Ranking.rank.asc())
        )
    ).all()
    return [place for place, _rank in rows]


@router.get("/{place_id}", response_model=PlaceDetail)
async def get_place(
    mission_id: str,
    place_id: str,
    _: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> Place:
    """Detail view. Membership of the path mission is sufficient — we
    don't enforce that the place is in *this* mission's shortlist; a
    member who saw a link from a prior run can still inspect it."""
    place = (
        await session.execute(select(Place).where(Place.id == place_id))
    ).scalar_one_or_none()
    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="place not found",
        )
    return place


@router.post(
    "/refresh",
    response_model=PlaceRefreshOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def refresh_places(
    mission_id: str,
    _: MissionMember = Depends(get_mission_owner),
) -> PlaceRefreshOut:
    """Owner-only: kick a fresh recommend graph run for this mission.

    Returns the new ``agent_run_id`` immediately (202); the graph drives
    in the background and pauses at the HITL gate. The client polls
    ``GET /agents/runs/{id}`` to track progress and POSTs to
    ``/agents/runs/{id}/approve`` (or reject) to resume."""
    agent_run_id = await graph_service.kick_recommend(
        mission_id,
        trigger="places_refresh",
    )
    return PlaceRefreshOut(agent_run_id=agent_run_id)
