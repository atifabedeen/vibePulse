from __future__ import annotations

"""`/api/v1/missions/{mission_id}/preferences` (sec 7.4).

* `PUT  /me`         — upsert the caller's preference row for the mission.
* `GET  /`           — list all members' preference rows for the mission.
* `POST /me/parse`   — runs JUST the ``parse_preferences`` LangGraph node
                       against the caller's raw comment + their existing
                       structured preference snapshot, persists the
                       parsed scalar fields back onto the row, stamps
                       ``parsed_at``, and returns the updated row.
                       Synchronous (one LLM call, ~ms in stub mode).
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.mission import MissionMember
from app.models.preference import Preference
from app.schemas.preference import (
    PreferenceOut,
    PreferenceParseIn,
    PreferencePayload,
)
from app.security.deps import get_mission_member
from app.services import graph_service

router = APIRouter(
    prefix="/missions/{mission_id}/preferences",
    tags=["preferences"],
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _apply_payload(row: Preference, payload: PreferencePayload) -> None:
    """Copy non-None fields from payload onto an existing Preference row."""
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)


@router.put(
    "/me",
    response_model=PreferenceOut,
    status_code=status.HTTP_200_OK,
)
async def put_my_preferences(
    mission_id: str,
    payload: PreferencePayload,
    member: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> Preference:
    """Upsert (mission_id, user_id) row from `payload`."""
    user_id = member.user_id
    existing = (
        await session.execute(
            select(Preference).where(
                Preference.mission_id == mission_id,
                Preference.user_id == user_id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        # Build a new row, defaulting array fields to [] when omitted.
        data = payload.model_dump(exclude_unset=True)
        row = Preference(
            mission_id=mission_id,
            user_id=user_id,
            cuisines_like=data.get("cuisines_like") or [],
            cuisines_dislike=data.get("cuisines_dislike") or [],
            dietary_restrictions=data.get("dietary_restrictions") or [],
            budget_max_cents=data.get("budget_max_cents"),
            distance_tolerance_m=data.get("distance_tolerance_m"),
            vibe=data.get("vibe"),
            noise_tolerance=data.get("noise_tolerance"),
            seating_preference=data.get("seating_preference"),
            urgency=data.get("urgency"),
            hunger_level=data.get("hunger_level"),
            raw_comment=data.get("raw_comment"),
        )
        session.add(row)
        await session.flush()
        return row

    _apply_payload(existing, payload)
    existing.updated_at = _utcnow()
    await session.flush()
    return existing


@router.get("/", response_model=List[PreferenceOut])
async def list_preferences(
    mission_id: str,
    _: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> List[Preference]:
    rows = (
        await session.execute(
            select(Preference).where(Preference.mission_id == mission_id)
        )
    ).scalars().all()
    return list(rows)


@router.post("/me/parse", response_model=PreferenceOut)
async def parse_my_preferences(
    mission_id: str,
    payload: PreferenceParseIn,
    member: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> Preference:
    """Run JUST the ``parse_preferences`` LangGraph node against the
    caller's ``raw_comment`` + the structured fields already on their
    Preference row, then merge the parsed scalar/list fields back onto
    the row and stamp ``parsed_at``. Synchronous — the parse node is
    one LLM call (a stub keyword-spotter in dev) so we don't bother
    with a background task here.
    """
    user_id = member.user_id
    existing = (
        await session.execute(
            select(Preference).where(
                Preference.mission_id == mission_id,
                Preference.user_id == user_id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        existing = Preference(
            mission_id=mission_id,
            user_id=user_id,
            cuisines_like=[],
            cuisines_dislike=[],
            dietary_restrictions=[],
        )
        session.add(existing)

    # Snapshot the current structured prefs so the parse node can layer
    # the parsed comment on top without losing existing explicit values.
    structured: Dict[str, Any] = {
        "budget_max_cents": existing.budget_max_cents,
        "distance_tolerance_m": existing.distance_tolerance_m,
        "cuisines_like": list(existing.cuisines_like or []),
        "cuisines_dislike": list(existing.cuisines_dislike or []),
        "dietary_restrictions": list(existing.dietary_restrictions or []),
        "vibe": existing.vibe,
        "noise_tolerance": existing.noise_tolerance,
        "seating_preference": existing.seating_preference,
        "urgency": existing.urgency,
        "hunger_level": existing.hunger_level,
    }

    parsed = await graph_service.parse_only(
        raw_comment=payload.raw_comment,
        structured=structured,
    )

    # Merge parsed view back onto the row. Scalar fields: parsed value
    # wins ONLY when there's no existing value (explicit > inferred).
    # List fields: parsed values get merged into the existing list
    # (preserve order, dedupe). This mirrors the merge rules inside
    # parse_preferences itself.
    for key in (
        "budget_max_cents",
        "distance_tolerance_m",
        "vibe",
        "noise_tolerance",
        "seating_preference",
    ):
        if getattr(existing, key) in (None, ""):
            new_val = parsed.get(key)
            if new_val is not None:
                setattr(existing, key, new_val)

    for key in ("cuisines_like", "cuisines_dislike", "dietary_restrictions"):
        cur = list(getattr(existing, key) or [])
        for item in parsed.get(key) or []:
            if item not in cur:
                cur.append(item)
        setattr(existing, key, cur)

    existing.raw_comment = payload.raw_comment
    existing.parsed_at = _utcnow()
    existing.updated_at = _utcnow()
    await session.flush()
    return existing
