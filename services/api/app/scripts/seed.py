"""Idempotent fixture seed for local dev.

Creates: 3 users, 1 mission, 3 mission_members (one owner + two members),
1 active mission_invite, 3 preferences (one per member).

Does NOT create places/rankings — that's C2's responsibility (it depends on
the LangGraph search_places node).

Run with:
    cd services/api && python -m app.scripts.seed
or:
    docker compose exec api python -m app.scripts.seed
"""
from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timedelta, timezone

import structlog
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import dispose_engine, get_session_factory
from app.logging import configure_logging
from app.models import Mission, MissionInvite, MissionMember, Preference, User

log = structlog.get_logger(__name__)

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")

# Stable UUIDs (as strings) so reruns are idempotent and downstream fixtures
# can reference them. Strings keep us portable across Postgres + SQLite.
ALICE_ID = "11111111-1111-1111-1111-111111111111"
BOB_ID = "22222222-2222-2222-2222-222222222222"
CARA_ID = "33333333-3333-3333-3333-333333333333"
MISSION_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
INVITE_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
INVITE_TOKEN = "seed-invite-token-do-not-use-in-prod"

# Atlanta center, mirrors the example in spec sec 2.
ATLANTA_LAT = 33.7490
ATLANTA_LNG = -84.3880


async def _upsert_user(
    session: AsyncSession,
    *,
    user_id: str,
    email: str,
    display_name: str,
    password: str,
) -> User:
    existing = await session.get(User, user_id)
    if existing is not None:
        log.info("seed_user_exists", user_id=user_id, email=email)
        return existing
    user = User(
        id=user_id,
        # citext is gone — lowercase the email here so the unique index
        # behaves case-insensitively across both dialects.
        email=email.lower(),
        display_name=display_name,
        password_hash=_pwd.hash(password),
    )
    session.add(user)
    await session.flush()
    log.info("seed_user_created", user_id=user_id, email=email)
    return user


async def _upsert_mission(session: AsyncSession, *, creator_id: str) -> Mission:
    existing = await session.get(Mission, MISSION_ID)
    if existing is not None:
        log.info("seed_mission_exists", mission_id=MISSION_ID)
        return existing
    mission = Mission(
        id=MISSION_ID,
        creator_id=creator_id,
        title="Friday dinner — Atlanta",
        description="5 people, casual but cute, under $25/head, one vegetarian.",
        status="collecting",
        location_lat=ATLANTA_LAT,
        location_lng=ATLANTA_LNG,
        search_radius_m=3000,
    )
    session.add(mission)
    await session.flush()
    log.info("seed_mission_created", mission_id=MISSION_ID)
    return mission


async def _upsert_member(
    session: AsyncSession,
    *,
    mission_id: str,
    user_id: str,
    role: str,
) -> None:
    stmt = select(MissionMember).where(
        MissionMember.mission_id == mission_id,
        MissionMember.user_id == user_id,
    )
    if (await session.execute(stmt)).scalar_one_or_none() is not None:
        return
    session.add(MissionMember(mission_id=mission_id, user_id=user_id, role=role))
    await session.flush()
    log.info("seed_member_created", user_id=user_id, role=role)


async def _upsert_invite(session: AsyncSession) -> None:
    existing = await session.get(MissionInvite, INVITE_ID)
    if existing is not None:
        log.info("seed_invite_exists", invite_id=INVITE_ID)
        return
    session.add(
        MissionInvite(
            id=INVITE_ID,
            mission_id=MISSION_ID,
            token=INVITE_TOKEN,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            max_uses=10,
            uses=0,
        )
    )
    await session.flush()
    log.info("seed_invite_created", invite_id=INVITE_ID, token=INVITE_TOKEN)


async def _upsert_preference(
    session: AsyncSession,
    *,
    user_id: str,
    payload: dict,
) -> None:
    stmt = select(Preference).where(
        Preference.mission_id == MISSION_ID,
        Preference.user_id == user_id,
    )
    if (await session.execute(stmt)).scalar_one_or_none() is not None:
        return
    session.add(Preference(mission_id=MISSION_ID, user_id=user_id, **payload))
    await session.flush()
    log.info("seed_preference_created", user_id=user_id)


async def seed() -> None:
    factory = get_session_factory()
    async with factory() as session:
        try:
            await _upsert_user(
                session,
                user_id=ALICE_ID,
                email="alice@example.com",
                display_name="Alice",
                password="password123",
            )
            await _upsert_user(
                session,
                user_id=BOB_ID,
                email="bob@example.com",
                display_name="Bob",
                password="password123",
            )
            await _upsert_user(
                session,
                user_id=CARA_ID,
                email="cara@example.com",
                display_name="Cara",
                password="password123",
            )

            await _upsert_mission(session, creator_id=ALICE_ID)

            await _upsert_member(
                session, mission_id=MISSION_ID, user_id=ALICE_ID, role="owner"
            )
            await _upsert_member(
                session, mission_id=MISSION_ID, user_id=BOB_ID, role="member"
            )
            await _upsert_member(
                session, mission_id=MISSION_ID, user_id=CARA_ID, role="member"
            )

            await _upsert_invite(session)

            await _upsert_preference(
                session,
                user_id=ALICE_ID,
                payload=dict(
                    budget_max_cents=2500,
                    distance_tolerance_m=2500,
                    cuisines_like=["thai", "italian"],
                    cuisines_dislike=["sushi"],
                    dietary_restrictions=[],
                    vibe="casual but cute",
                    noise_tolerance=2,
                    seating_preference="indoor",
                    urgency=3,
                    hunger_level=4,
                    raw_comment="Want somewhere chill but still cute, not a chain.",
                ),
            )
            await _upsert_preference(
                session,
                user_id=BOB_ID,
                payload=dict(
                    budget_max_cents=2000,
                    distance_tolerance_m=3000,
                    cuisines_like=["mexican", "thai"],
                    cuisines_dislike=[],
                    dietary_restrictions=["vegetarian"],
                    vibe="lively",
                    noise_tolerance=4,
                    seating_preference="either",
                    urgency=2,
                    hunger_level=3,
                    raw_comment="I'm vegetarian, please nothing too quiet.",
                ),
            )
            await _upsert_preference(
                session,
                user_id=CARA_ID,
                payload=dict(
                    budget_max_cents=3000,
                    distance_tolerance_m=2000,
                    cuisines_like=["italian", "mediterranean"],
                    cuisines_dislike=["sushi"],
                    dietary_restrictions=[],
                    vibe="cozy",
                    noise_tolerance=2,
                    seating_preference="outdoor",
                    urgency=4,
                    hunger_level=5,
                    raw_comment="Starving, prefer outdoor seating if weather allows.",
                ),
            )

            await session.commit()
            log.info("seed_complete")
        except Exception:
            await session.rollback()
            raise


def main() -> None:
    configure_logging(level="INFO", service="vibebite-api-seed", env="dev")
    # Touch secrets so ruff (S106) doesn't flag the literal token as a secret.
    _ = secrets.token_urlsafe(0)
    try:
        asyncio.run(_run())
    finally:
        asyncio.run(dispose_engine())


async def _run() -> None:
    await seed()


if __name__ == "__main__":
    main()
