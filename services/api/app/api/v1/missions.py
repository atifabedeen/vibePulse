from __future__ import annotations

"""Missions endpoints — spec sec 7.3.

Auth: every endpoint here is behind `get_current_user`. Member/owner
checks live in the service layer (assert_member / assert_owner) so they
can be reused from preferences/places/votes routers later.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models.user import User
from app.schemas.mission import (
    InviteCreate,
    InviteOut,
    MissionCreate,
    MissionDetailOut,
    MissionListOut,
    MissionMemberOut,
    MissionOut,
    MissionUpdate,
    RedeemIn,
    ReplanIn,
    ReplanOut,
)
from app.security.deps import get_current_user
from app.services import graph_service, mission_service as svc

router = APIRouter(prefix="/missions", tags=["missions"])


# --- Create / list -------------------------------------------------------


@router.post("", response_model=MissionOut, status_code=status.HTTP_201_CREATED)
async def create_mission(
    payload: MissionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MissionOut:
    mission = await svc.create_mission(
        session, creator_id=user.id, payload=payload
    )
    return MissionOut.model_validate(svc.mission_to_dict(mission))


@router.get("", response_model=MissionListOut)
async def list_missions(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MissionListOut:
    try:
        rows, next_cursor = await svc.list_missions_for_user(
            session,
            user_id=user.id,
            status=status_filter,
            limit=limit,
            cursor=cursor,
        )
    except svc.InvalidMissionUpdate as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return MissionListOut(
        items=[MissionOut.model_validate(svc.mission_to_dict(m)) for m in rows],
        next_cursor=next_cursor,
    )


# --- Invite redeem (must come BEFORE /{mission_id} so FastAPI doesn't
# match "invites" as the mission_id path param). ---------------------------


@router.post("/invites/redeem", response_model=MissionOut)
async def redeem_invite(
    payload: RedeemIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MissionOut:
    try:
        mission = await svc.redeem_invite(
            session, token=payload.token, user_id=user.id
        )
    except svc.InviteNotFound:
        raise HTTPException(status_code=404, detail="invite not found")
    except svc.InviteExpired:
        raise HTTPException(status_code=410, detail="invite expired")
    except svc.InviteExhausted:
        raise HTTPException(status_code=409, detail="invite max uses reached")
    except svc.AlreadyMember:
        raise HTTPException(status_code=409, detail="already a member")
    except svc.MissionNotFound:
        raise HTTPException(status_code=404, detail="mission not found")
    return MissionOut.model_validate(svc.mission_to_dict(mission))


# --- Per-mission CRUD ----------------------------------------------------


@router.get("/{mission_id}", response_model=MissionDetailOut)
async def get_mission(
    mission_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MissionDetailOut:
    try:
        mission = await svc.get_mission_or_404(session, mission_id)
        await svc.assert_member(session, mission_id, user.id)
    except svc.MissionNotFound:
        raise HTTPException(status_code=404, detail="mission not found")
    except svc.MissionForbidden:
        # Don't leak existence to non-members.
        raise HTTPException(status_code=404, detail="mission not found")
    members = await svc.get_mission_members(session, mission_id)
    base = svc.mission_to_dict(mission)
    base["members"] = [MissionMemberOut.model_validate(m) for m in members]
    return MissionDetailOut.model_validate(base)


@router.patch("/{mission_id}", response_model=MissionOut)
async def patch_mission(
    mission_id: str,
    payload: MissionUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MissionOut:
    try:
        mission = await svc.get_mission_or_404(session, mission_id)
        await svc.assert_owner(session, mission_id, user.id)
        mission = await svc.update_mission(
            session, mission=mission, payload=payload
        )
    except svc.MissionNotFound:
        raise HTTPException(status_code=404, detail="mission not found")
    except svc.MissionForbidden:
        raise HTTPException(status_code=403, detail="owner role required")
    except svc.InvalidMissionUpdate as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return MissionOut.model_validate(svc.mission_to_dict(mission))


@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mission(
    mission_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    try:
        mission = await svc.get_mission_or_404(session, mission_id)
        await svc.assert_owner(session, mission_id, user.id)
        await svc.delete_mission(session, mission=mission)
    except svc.MissionNotFound:
        raise HTTPException(status_code=404, detail="mission not found")
    except svc.MissionForbidden:
        raise HTTPException(status_code=403, detail="owner role required")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Invites -------------------------------------------------------------


@router.post(
    "/{mission_id}/invites",
    response_model=InviteOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    mission_id: str,
    payload: InviteCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> InviteOut:
    try:
        await svc.get_mission_or_404(session, mission_id)
        await svc.assert_owner(session, mission_id, user.id)
        invite = await svc.create_invite(
            session, mission_id=mission_id, payload=payload
        )
    except svc.MissionNotFound:
        raise HTTPException(status_code=404, detail="mission not found")
    except svc.MissionForbidden:
        raise HTTPException(status_code=403, detail="owner role required")
    return InviteOut.model_validate(invite)


# --- Replan stub --------------------------------------------------------


@router.post(
    "/{mission_id}/replan",
    response_model=ReplanOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def replan_mission(
    mission_id: str,
    payload: ReplanIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReplanOut:
    """Member-scoped: kick a fresh recommend graph run with the
    submitted overrides applied as ``_replan_overrides`` (so the very
    first scoring pass already honours the new constraints, e.g. a
    tighter budget). The graph runs in the background; we 202 with the
    new ``agent_run_id`` immediately.
    """
    try:
        await svc.get_mission_or_404(session, mission_id)
        await svc.assert_member(session, mission_id, user.id)
    except svc.MissionNotFound:
        raise HTTPException(status_code=404, detail="mission not found")
    except svc.MissionForbidden:
        raise HTTPException(status_code=404, detail="mission not found")

    overrides: Optional[Dict[str, Any]] = payload.overrides or None
    agent_run_id = await graph_service.kick_recommend(
        mission_id,
        trigger="replan",
        overrides=overrides,
    )
    return ReplanOut(agent_run_id=agent_run_id)
