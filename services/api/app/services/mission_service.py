from __future__ import annotations

"""Mission service layer — pure DB logic, no FastAPI / HTTP types.

Routes call into here so we can unit-test mission creation, invite
redemption, etc. without spinning up a TestClient. Errors surface as the
small set of typed exceptions defined below; the route layer translates
them to HTTPExceptions.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mission import Mission, MissionInvite, MissionMember
from app.schemas.mission import (
    InviteCreate,
    LatLng,
    MissionCreate,
    MissionUpdate,
)

_ALLOWED_STATUSES = {
    "draft",
    "collecting",
    "ranking",
    "voting",
    "decided",
    "cancelled",
}


# --- Typed errors ----------------------------------------------------------
# Routes catch these and map to specific HTTP statuses. Keeping them here
# means the service layer stays framework-agnostic.

class MissionNotFound(Exception):
    pass


class MissionForbidden(Exception):
    """Caller is authenticated but not a member / not the owner."""


class InvalidMissionUpdate(Exception):
    pass


class InviteNotFound(Exception):
    pass


class InviteExpired(Exception):
    pass


class InviteExhausted(Exception):
    pass


class AlreadyMember(Exception):
    pass


# --- Helpers ---------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_token() -> str:
    """32-char URL-safe random token. token_urlsafe(24) -> 32 chars."""
    return secrets.token_urlsafe(24)


def _ensure_aware(dt: datetime) -> datetime:
    """SQLite drops tz info on round-trip; coerce to UTC for safe compare."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def mission_to_dict(m: Mission) -> dict:
    """Shape a Mission ORM row into the {location: {lat,lng}} wire shape."""
    return {
        "id": m.id,
        "creator_id": m.creator_id,
        "title": m.title,
        "description": m.description,
        "status": m.status,
        "location": LatLng(lat=m.location_lat, lng=m.location_lng),
        "search_radius_m": m.search_radius_m,
        "scheduled_for": m.scheduled_for,
        "winner_place_id": m.winner_place_id,
        "backup_place_id": m.backup_place_id,
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }


# --- Authz helpers ---------------------------------------------------------

async def get_mission_or_404(session: AsyncSession, mission_id: str) -> Mission:
    m = await session.get(Mission, mission_id)
    if m is None:
        raise MissionNotFound(mission_id)
    return m


async def assert_member(
    session: AsyncSession, mission_id: str, user_id: str
) -> MissionMember:
    stmt = select(MissionMember).where(
        MissionMember.mission_id == mission_id,
        MissionMember.user_id == user_id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise MissionForbidden("not a member of this mission")
    return row


async def assert_owner(
    session: AsyncSession, mission_id: str, user_id: str
) -> MissionMember:
    member = await assert_member(session, mission_id, user_id)
    if member.role != "owner":
        raise MissionForbidden("owner role required")
    return member


# --- CRUD -----------------------------------------------------------------

async def create_mission(
    session: AsyncSession, *, creator_id: str, payload: MissionCreate
) -> Mission:
    mission = Mission(
        id=str(uuid.uuid4()),
        creator_id=creator_id,
        title=payload.title,
        description=payload.description,
        status="collecting",
        location_lat=payload.location.lat,
        location_lng=payload.location.lng,
        search_radius_m=payload.search_radius_m,
        scheduled_for=payload.scheduled_for,
    )
    session.add(mission)
    # Auto-create the owner row so every mission has at least one member
    # (this is what the GET-list query joins on).
    session.add(
        MissionMember(
            mission_id=mission.id,
            user_id=creator_id,
            role="owner",
        )
    )
    await session.flush()
    return mission


async def list_missions_for_user(
    session: AsyncSession,
    *,
    user_id: str,
    status: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
) -> Tuple[List[Mission], Optional[str]]:
    """List missions the user is a member of, newest-first.

    Cursor is the ISO timestamp of the last item from the previous page;
    we filter `created_at < cursor` for a stable, monotonic page boundary.
    """
    stmt = (
        select(Mission)
        .join(MissionMember, MissionMember.mission_id == Mission.id)
        .where(MissionMember.user_id == user_id)
        .order_by(desc(Mission.created_at), desc(Mission.id))
        .limit(limit + 1)  # peek one ahead to know if there's another page
    )
    if status is not None:
        stmt = stmt.where(Mission.status == status)
    if cursor is not None:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError as exc:
            raise InvalidMissionUpdate(f"bad cursor: {cursor}") from exc
        stmt = stmt.where(Mission.created_at < cursor_dt)

    rows = (await session.execute(stmt)).scalars().all()
    next_cursor: Optional[str] = None
    if len(rows) > limit:
        rows = rows[:limit]
        # Cursor = created_at of the last returned row, ISO format.
        next_cursor = _ensure_aware(rows[-1].created_at).isoformat()
    return list(rows), next_cursor


async def get_mission_members(
    session: AsyncSession, mission_id: str
) -> List[MissionMember]:
    stmt = select(MissionMember).where(MissionMember.mission_id == mission_id)
    return list((await session.execute(stmt)).scalars().all())


async def update_mission(
    session: AsyncSession, *, mission: Mission, payload: MissionUpdate
) -> Mission:
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in _ALLOWED_STATUSES:
        raise InvalidMissionUpdate(f"bad status: {data['status']}")
    if "location" in data and data["location"] is not None:
        loc = data.pop("location")
        # location may already be a dict or a LatLng depending on validator path
        if isinstance(loc, dict):
            mission.location_lat = loc["lat"]
            mission.location_lng = loc["lng"]
        else:
            mission.location_lat = loc.lat
            mission.location_lng = loc.lng
    for key in ("title", "description", "search_radius_m", "scheduled_for", "status"):
        if key in data:
            setattr(mission, key, data[key])
    mission.updated_at = _utcnow()
    await session.flush()
    return mission


async def delete_mission(session: AsyncSession, *, mission: Mission) -> None:
    """Hard delete. mission_members and mission_invites cascade via FK."""
    await session.delete(mission)
    await session.flush()


# --- Invites --------------------------------------------------------------

async def create_invite(
    session: AsyncSession, *, mission_id: str, payload: InviteCreate
) -> MissionInvite:
    invite = MissionInvite(
        id=str(uuid.uuid4()),
        mission_id=mission_id,
        token=_new_token(),
        expires_at=_utcnow() + timedelta(hours=payload.expires_in_hours),
        max_uses=payload.max_uses,
        uses=0,
    )
    session.add(invite)
    await session.flush()
    return invite


async def redeem_invite(
    session: AsyncSession, *, token: str, user_id: str
) -> Mission:
    stmt = select(MissionInvite).where(MissionInvite.token == token)
    invite = (await session.execute(stmt)).scalar_one_or_none()
    if invite is None:
        raise InviteNotFound(token)

    expires_at = _ensure_aware(invite.expires_at)
    if expires_at <= _utcnow():
        raise InviteExpired(token)
    if invite.uses >= invite.max_uses:
        raise InviteExhausted(token)

    # If they're already a member, surface that distinctly so the route can
    # 200 idempotently rather than 409.
    existing_stmt = select(MissionMember).where(
        MissionMember.mission_id == invite.mission_id,
        MissionMember.user_id == user_id,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    mission = await get_mission_or_404(session, invite.mission_id)

    if existing is not None:
        raise AlreadyMember(invite.mission_id)

    invite.uses = invite.uses + 1
    session.add(
        MissionMember(
            mission_id=invite.mission_id,
            user_id=user_id,
            role="member",
        )
    )
    await session.flush()
    return mission


# --- Replan stub ---------------------------------------------------------

def make_stub_agent_run_id() -> str:
    """C5-D will replace this with a real LangGraph dispatch."""
    return f"stub-{uuid.uuid4()}"
