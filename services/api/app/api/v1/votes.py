from __future__ import annotations

"""`/api/v1/missions/{mission_id}/votes` (sec 7.7).

* `PUT  /me`        — upsert (mission_id, user_id, place_id) row.
                       weight ∈ {-1, 1}: 1 = upvote, -1 = veto.
* `GET  /`          — `{tally: {place_id: {up, veto}}}` aggregation.
* `POST /finalize`  — owner-only. Picks the place with the highest
                       (up - veto) score; ties broken by higher up
                       count; second-place becomes the backup. Writes
                       both onto the missions row and returns the pair.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.mission import Mission, MissionMember
from app.models.place import Place
from app.models.vote import Vote
from app.schemas.place import PlaceOut
from app.schemas.vote import (
    FinalizeOut,
    VoteCounts,
    VoteOut,
    VotePayload,
    VoteTally,
)
from app.security.deps import get_mission_member, get_mission_owner

router = APIRouter(
    prefix="/missions/{mission_id}/votes",
    tags=["votes"],
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.put("/me", response_model=List[VoteOut])
async def put_my_vote(
    mission_id: str,
    payload: VotePayload,
    member: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> List[Vote]:
    """Upsert this caller's vote on `payload.place_id`. The full set of
    the caller's votes for the mission is returned — that's a more useful
    list shape for the mobile UI than just the row that was changed."""
    user_id = member.user_id

    # Verify the place exists. We don't hard-require it to be in the
    # mission's current shortlist (rankings can churn between submissions),
    # but a reference to a non-existent place is still a 404 / 409.
    place = (
        await session.execute(select(Place).where(Place.id == payload.place_id))
    ).scalar_one_or_none()
    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="place not found",
        )

    existing = (
        await session.execute(
            select(Vote).where(
                Vote.mission_id == mission_id,
                Vote.user_id == user_id,
                Vote.place_id == payload.place_id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = Vote(
            mission_id=mission_id,
            user_id=user_id,
            place_id=payload.place_id,
            weight=payload.weight,
        )
        session.add(existing)
    else:
        existing.weight = payload.weight
        existing.created_at = _utcnow()
    await session.flush()

    rows = (
        await session.execute(
            select(Vote).where(
                Vote.mission_id == mission_id,
                Vote.user_id == user_id,
            )
        )
    ).scalars().all()
    return list(rows)


@router.get("/", response_model=VoteTally)
async def vote_tally(
    mission_id: str,
    _: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> VoteTally:
    rows = (
        await session.execute(
            select(Vote).where(Vote.mission_id == mission_id)
        )
    ).scalars().all()

    tally: Dict[str, VoteCounts] = {}
    for v in rows:
        bucket = tally.setdefault(v.place_id, VoteCounts())
        if v.weight > 0:
            bucket.up += 1
        else:
            bucket.veto += 1
    return VoteTally(tally=tally)


def _pick_winner_and_backup(
    tally: Dict[str, VoteCounts],
) -> Tuple[Optional[str], Optional[str]]:
    """Return (winner_place_id, backup_place_id) by (up - veto) desc,
    breaking ties with up count, then place_id for determinism."""
    if not tally:
        return None, None
    ranked = sorted(
        tally.items(),
        key=lambda item: (
            -(item[1].up - item[1].veto),
            -item[1].up,
            item[0],
        ),
    )
    winner = ranked[0][0] if ranked else None
    backup = ranked[1][0] if len(ranked) > 1 else None
    return winner, backup


@router.post("/finalize", response_model=FinalizeOut)
async def finalize_votes(
    mission_id: str,
    _: MissionMember = Depends(get_mission_owner),
    session: AsyncSession = Depends(get_session),
) -> FinalizeOut:
    """Aggregate votes, pick winner + backup, persist on the mission."""
    rows = (
        await session.execute(
            select(Vote).where(Vote.mission_id == mission_id)
        )
    ).scalars().all()

    tally: Dict[str, VoteCounts] = {}
    for v in rows:
        bucket = tally.setdefault(v.place_id, VoteCounts())
        if v.weight > 0:
            bucket.up += 1
        else:
            bucket.veto += 1

    winner_id, backup_id = _pick_winner_and_backup(tally)

    mission = (
        await session.execute(select(Mission).where(Mission.id == mission_id))
    ).scalar_one_or_none()
    # `get_mission_owner` already 404s if the mission is gone, so this is
    # really just a guard for the type-checker.
    if mission is None:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="mission not found",
        )
    mission.winner_place_id = winner_id
    mission.backup_place_id = backup_id
    mission.updated_at = _utcnow()

    winner_place: Optional[Place] = None
    backup_place: Optional[Place] = None
    if winner_id is not None:
        winner_place = (
            await session.execute(select(Place).where(Place.id == winner_id))
        ).scalar_one_or_none()
    if backup_id is not None:
        backup_place = (
            await session.execute(select(Place).where(Place.id == backup_id))
        ).scalar_one_or_none()

    await session.flush()

    return FinalizeOut(
        winner=PlaceOut.model_validate(winner_place) if winner_place else None,
        backup=PlaceOut.model_validate(backup_place) if backup_place else None,
    )
