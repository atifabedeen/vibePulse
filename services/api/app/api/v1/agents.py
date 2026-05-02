from __future__ import annotations

"""`/api/v1/missions/{mission_id}/agents` (spec sec 7.8).

* `GET  /runs`               — list AgentRun rows for the mission, newest first.
* `GET  /runs/{run_id}`      — detail: AgentRun + ordered AgentRunStep rows.
* `POST /runs/{run_id}/approve` — owner-only. Resumes the HITL graph with
                                  ``Command(resume={"decision":"approve"})``.
* `POST /runs/{run_id}/reject`  — owner-only. Resumes with reject + a
                                  free-form reason and optional
                                  ``overrides`` dict (e.g. lower the
                                  ``budget_max_cents`` cap).

The actual graph drive happens in a background task spawned by
``graph_service.resume_with_decision`` so the HTTP response returns
immediately.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.agent_run import AgentRun, AgentRunStep
from app.models.mission import MissionMember
from app.schemas.agent import (
    AgentRejectIn,
    AgentResumeOut,
    AgentRunDetail,
    AgentRunOut,
    AgentRunStepOut,
)
from app.security.deps import get_mission_member, get_mission_owner
from app.services import graph_service

router = APIRouter(
    prefix="/missions/{mission_id}/agents",
    tags=["agents"],
)


@router.get("/runs", response_model=List[AgentRunOut])
async def list_agent_runs(
    mission_id: str,
    _: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> List[AgentRun]:
    """Member-scoped: every AgentRun for the mission, newest first."""
    rows = (
        await session.execute(
            select(AgentRun)
            .where(AgentRun.mission_id == mission_id)
            .order_by(AgentRun.started_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/runs/{run_id}", response_model=AgentRunDetail)
async def get_agent_run(
    mission_id: str,
    run_id: str,
    _: MissionMember = Depends(get_mission_member),
    session: AsyncSession = Depends(get_session),
) -> AgentRunDetail:
    """Member-scoped detail view: the run + its ordered step rows."""
    run = (
        await session.execute(
            select(AgentRun).where(
                AgentRun.id == run_id,
                AgentRun.mission_id == mission_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="agent run not found",
        )
    steps = (
        await session.execute(
            select(AgentRunStep)
            .where(AgentRunStep.agent_run_id == run_id)
            .order_by(AgentRunStep.started_at.asc())
        )
    ).scalars().all()
    base = AgentRunOut.model_validate(run).model_dump()
    base["steps"] = [AgentRunStepOut.model_validate(s) for s in steps]
    return AgentRunDetail.model_validate(base)


@router.post("/runs/{run_id}/approve", response_model=AgentResumeOut)
async def approve_agent_run(
    mission_id: str,
    run_id: str,
    _: MissionMember = Depends(get_mission_owner),
    session: AsyncSession = Depends(get_session),
) -> AgentResumeOut:
    """Owner-only: resume the HITL graph with an approval decision."""
    # Verify the run exists and belongs to this mission BEFORE we kick
    # off the resume task — avoids spawning a task that immediately
    # errors out.
    run = (
        await session.execute(
            select(AgentRun).where(
                AgentRun.id == run_id,
                AgentRun.mission_id == mission_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="agent run not found",
        )
    new_status = await graph_service.resume_with_decision(run_id, "approve")
    return AgentResumeOut(agent_run_id=run_id, status=new_status)


@router.post("/runs/{run_id}/reject", response_model=AgentResumeOut)
async def reject_agent_run(
    mission_id: str,
    run_id: str,
    payload: AgentRejectIn,
    _: MissionMember = Depends(get_mission_owner),
    session: AsyncSession = Depends(get_session),
) -> AgentResumeOut:
    """Owner-only: resume the HITL graph with reject + replan overrides."""
    run = (
        await session.execute(
            select(AgentRun).where(
                AgentRun.id == run_id,
                AgentRun.mission_id == mission_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="agent run not found",
        )
    new_status = await graph_service.resume_with_decision(
        run_id,
        "reject",
        overrides=payload.overrides,
        reason=payload.reason,
    )
    return AgentResumeOut(agent_run_id=run_id, status=new_status)
