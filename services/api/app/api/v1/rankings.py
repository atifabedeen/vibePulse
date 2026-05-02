from __future__ import annotations

"""`/api/v1/missions/{mission_id}/rankings` (sec 7.6).

* `GET /latest`            — newest agent_run's rankings.
* `GET /runs/{agent_run_id}` — rankings for a specific run.

Both responses return `{agent_run_id, items: Ranking[]}`. `items` is
sorted by `rank` ascending so position 0 is the top pick.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.mission import MissionMember
from app.models.ranking import Ranking
from app.schemas.ranking import RankingBatch, RankingItem
from app.security.deps import get_mission_member

router = APIRouter(
    prefix="/missions/{mission_id}/rankings",
    tags=["rankings"],
)


@router.get("/latest", response_model=RankingBatch)
async def latest_rankings(
    mission_id: str,
    _: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> RankingBatch:
    """Pick the most recent ranking row for the mission, take its
    `agent_run_id`, then return every row tagged with that run id."""
    latest = (
        await session.execute(
            select(Ranking)
            .where(Ranking.mission_id == mission_id)
            .order_by(Ranking.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is None:
        return RankingBatch(agent_run_id=None, items=[])

    rows = (
        await session.execute(
            select(Ranking)
            .where(
                Ranking.mission_id == mission_id,
                Ranking.agent_run_id == latest.agent_run_id,
            )
            .order_by(Ranking.rank.asc())
        )
    ).scalars().all()

    return RankingBatch(
        agent_run_id=latest.agent_run_id,
        items=[RankingItem.model_validate(r) for r in rows],
    )


@router.get("/runs/{agent_run_id}", response_model=RankingBatch)
async def rankings_for_run(
    mission_id: str,
    agent_run_id: str,
    _: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> RankingBatch:
    rows = (
        await session.execute(
            select(Ranking)
            .where(
                Ranking.mission_id == mission_id,
                Ranking.agent_run_id == agent_run_id,
            )
            .order_by(Ranking.rank.asc())
        )
    ).scalars().all()
    return RankingBatch(
        agent_run_id=agent_run_id,
        items=[RankingItem.model_validate(r) for r in rows],
    )
