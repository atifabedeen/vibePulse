"""Bridge between the FastAPI surface and the LangGraph agent package.

The API never imports ``vibebite_agents.run_demo`` (that's the CLI demo
runner). Instead, this shim owns the small surface the HTTP routes need:

* ``kick_recommend(mission_id, trigger, overrides)`` — start a fresh
  recommend graph run for a mission. Builds the GraphState by reading
  ``mission_members`` + their ``preferences`` rows + the mission's
  lat/lng directly from the DB, writes an ``agent_runs`` row via
  ``vibebite_agents.audit.begin_run``, then drives the graph in the
  background using ``asyncio.create_task`` so the HTTP request handler
  can return ``202`` immediately.

* ``parse_only(raw_comment, structured)`` — runs only the
  ``parse_preferences`` LangGraph node against a synthetic single-member
  state and returns the merged constraints dict. Used by
  ``POST /preferences/me/parse`` for the synchronous LLM parse.

* ``resume_with_decision(agent_run_id, decision, overrides)`` — resumes
  a graph run that hit the HITL ``interrupt()`` gate. Uses the
  ``thread_id == agent_run_id`` convention so the API can find the
  paused checkpoint without sharing in-memory state.

We intentionally use the same ``AsyncSqliteSaver`` that ``run_demo``
points at (``services/api/vibebite.db``) so HITL state survives between
the kick request and the approve/reject request. Every time we touch
the graph we open a fresh saver inside an ``async with`` block — that
maps 1:1 onto LangGraph 0.6's async-context-manager API and avoids us
having to manage a long-lived saver instance ourselves.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from sqlalchemy import select

from app.database import get_session_factory
from app.models.mission import Mission, MissionMember
from app.models.preference import Preference

# The agents package is installed editable alongside the API.
from vibebite_agents.audit import begin_run, end_run, write_rankings
from vibebite_agents.graph import build_graph
from vibebite_agents.state import CandidatePlace, GraphState, MemberPref


# Same SQLite file the API uses; the checkpointer puts its state in
# its own ``checkpoints`` / ``writes`` tables that don't collide with
# the application schema. Using a file path means the checkpoint
# survives across requests, which is what HITL resume needs.
_CHECKPOINT_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "vibebite.db",
)


def _checkpoint_path() -> str:
    """Resolve to an absolute path so ``cd``-sensitive callers behave."""
    return os.path.abspath(_CHECKPOINT_DB)


def _structured_from_pref(pref: Preference) -> Dict[str, Any]:
    """Snapshot a Preference row into the dict shape the graph expects."""
    return {
        "budget_max_cents": pref.budget_max_cents,
        "distance_tolerance_m": pref.distance_tolerance_m,
        "cuisines_like": list(pref.cuisines_like or []),
        "cuisines_dislike": list(pref.cuisines_dislike or []),
        "dietary_restrictions": list(pref.dietary_restrictions or []),
        "vibe": pref.vibe,
        "noise_tolerance": pref.noise_tolerance,
        "seating_preference": pref.seating_preference,
        "urgency": pref.urgency,
        "hunger_level": pref.hunger_level,
    }


async def _build_state_from_db(
    mission_id: str,
    *,
    overrides: Optional[Dict[str, Any]] = None,
) -> GraphState:
    """Read the mission + members + their preferences from the DB and
    build the GraphState the graph expects. Members without a Preference
    row contribute an empty ``structured`` snapshot so the graph still
    sees them. ``overrides`` is stashed on group_constraints under the
    ``_replan_overrides`` sentinel key so the replan node can pick it up
    on the FIRST iteration too (otherwise the override would only apply
    to subsequent loops)."""
    factory = get_session_factory()
    async with factory() as session:
        mission = await session.get(Mission, mission_id)
        if mission is None:
            raise ValueError(f"mission {mission_id} not found")

        members = (
            await session.execute(
                select(MissionMember).where(MissionMember.mission_id == mission_id)
            )
        ).scalars().all()

        prefs = (
            await session.execute(
                select(Preference).where(Preference.mission_id == mission_id)
            )
        ).scalars().all()

    pref_by_user = {p.user_id: p for p in prefs}

    member_prefs: List[MemberPref] = []
    for m in members:
        p = pref_by_user.get(m.user_id)
        if p is not None:
            structured = _structured_from_pref(p)
            raw_comment = p.raw_comment
        else:
            structured = {}
            raw_comment = None
        member_prefs.append(
            MemberPref(
                user_id=UUID(m.user_id),
                structured=structured,
                raw_comment=raw_comment,
            )
        )

    # Seed group_constraints with replan overrides so the very first
    # score_candidates pass already honours them (e.g. tightening budget
    # via ``POST /missions/{id}/replan``).
    initial_constraints: Optional[Dict[str, Any]] = None
    if overrides:
        initial_constraints = {
            "_replan_reason": "api-triggered overrides",
            "_replan_overrides": dict(overrides),
            "_replan_iteration": 0,
        }

    return GraphState(
        mission_id=UUID(mission_id),
        member_prefs=member_prefs,
        location=(mission.location_lat, mission.location_lng),
        search_radius_m=int(mission.search_radius_m),
        group_constraints=initial_constraints,
        agent_run_id=uuid4(),
    )


async def _drive_graph_to_completion(
    *,
    agent_run_id: str,
    mission_id: str,
    initial_state_dict: Dict[str, Any],
) -> None:
    """Background task: run the graph from start to either END or the
    HITL interrupt. We don't try to auto-resume here — the API caller
    drives interrupts via ``resume_with_decision``. On reaching END we
    write final rankings + close out the agent_run row."""
    audit_holder: Dict[str, Optional[str]] = {"id": agent_run_id}
    config: Dict[str, Any] = {"configurable": {"thread_id": agent_run_id}}

    try:
        async with AsyncSqliteSaver.from_conn_string(_checkpoint_path()) as saver:
            graph = build_graph(audit_run_id_holder=audit_holder, checkpointer=saver)
            result = await graph.ainvoke(initial_state_dict, config=config)

            interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
            if interrupts:
                # Paused at HITL gate. Mark the run as interrupted so the
                # UI can surface "awaiting approval" without us having to
                # snoop into the checkpointer's tables.
                await end_run(
                    agent_run_id,
                    status="interrupted",
                    output_dict={"awaiting": "human_approval"},
                )
                return

            # Graph reached END without interrupting (rare for v1 — every
            # path goes through await_approval — but be defensive).
            await _finalize_succeeded_run(
                mission_id=mission_id,
                agent_run_id=agent_run_id,
                payload=result,
            )
    except Exception as exc:  # noqa: BLE001
        try:
            await end_run(
                agent_run_id,
                status="failed",
                output_dict=None,
                error=f"{type(exc).__name__}: {exc}",
            )
        except Exception:  # noqa: BLE001
            pass


async def _finalize_succeeded_run(
    *,
    mission_id: str,
    agent_run_id: str,
    payload: Any,
) -> None:
    """Write the final rankings batch + close out the agent_runs row."""
    candidates: List[CandidatePlace] = []
    shortlist: List[CandidatePlace] = []
    winner_summary: Optional[Dict[str, Any]] = None

    if isinstance(payload, dict):
        raw_short = payload.get("shortlist") or []
        for c in raw_short:
            shortlist.append(
                c if isinstance(c, CandidatePlace) else CandidatePlace.model_validate(c)
            )
        raw_cands = payload.get("candidates") or []
        for c in raw_cands:
            candidates.append(
                c if isinstance(c, CandidatePlace) else CandidatePlace.model_validate(c)
            )
        raw_winner = payload.get("winner")
        if raw_winner is not None:
            try:
                w = (
                    raw_winner
                    if isinstance(raw_winner, CandidatePlace)
                    else CandidatePlace.model_validate(raw_winner)
                )
                winner_summary = {"name": w.name, "score": w.score}
            except Exception:  # noqa: BLE001
                winner_summary = None

    top5 = shortlist if shortlist else candidates[:5]
    if top5:
        try:
            await write_rankings(
                mission_id=mission_id,
                agent_run_id=agent_run_id,
                ranked_candidates=top5,
            )
        except Exception:  # noqa: BLE001
            pass

    try:
        await end_run(
            agent_run_id,
            status="succeeded",
            output_dict={
                "candidate_count": len(candidates),
                "shortlist_size": len(shortlist),
                "final_winner": winner_summary,
            },
        )
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


async def kick_recommend(
    mission_id: str,
    *,
    trigger: str = "api",
    overrides: Optional[Dict[str, Any]] = None,
) -> str:
    """Start a fresh recommend run; return the new ``agent_run_id``.

    The graph runs in a background task spawned via
    ``asyncio.create_task`` so the HTTP handler can respond ``202``
    without blocking on Google Places, scoring, etc. The graph's HITL
    gate will pause the task; ``resume_with_decision`` continues it.
    """
    initial_state = await _build_state_from_db(mission_id, overrides=overrides)
    initial_state_dict = initial_state.model_dump()

    agent_run_id = await begin_run(
        mission_id=mission_id,
        graph_name="recommend_v1",
        trigger=trigger,
        input_dict={
            "mission_id": mission_id,
            "location": list(initial_state.location),
            "search_radius_m": initial_state.search_radius_m,
            "member_pref_count": len(initial_state.member_prefs),
            "overrides": dict(overrides) if overrides else None,
        },
    )

    asyncio.create_task(
        _drive_graph_to_completion(
            agent_run_id=agent_run_id,
            mission_id=mission_id,
            initial_state_dict=initial_state_dict,
        )
    )
    return agent_run_id


async def parse_only(
    raw_comment: str,
    structured: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run JUST the ``parse_preferences`` node against a synthetic
    single-member state. Returns the merged ``group_constraints`` dict
    minus internal ``_replan_*`` sentinels so it's safe to surface to
    the client."""
    # Late import: keeps startup time low and avoids reaching into the
    # agents internals from module load.
    from vibebite_agents.nodes.parse_preferences import parse_preferences

    member = MemberPref(
        user_id=uuid4(),
        structured=dict(structured or {}),
        raw_comment=raw_comment,
    )
    state = GraphState(
        mission_id=uuid4(),
        member_prefs=[member],
        location=(0.0, 0.0),
        search_radius_m=3000,
        agent_run_id=uuid4(),
    )
    result = await parse_preferences(state)
    constraints = dict(result.get("group_constraints") or {})
    # Drop internal replan sentinels + per-member breakdown (the caller
    # only wants the merged group view here).
    return {
        k: v
        for k, v in constraints.items()
        if not k.startswith("_replan_") and k != "per_member"
    }


async def resume_with_decision(
    agent_run_id: str,
    decision: str,
    *,
    overrides: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
) -> str:
    """Resume an interrupted graph run with the human decision.

    Returns the resulting AgentRun status ("running"/"succeeded"/...).
    The graph may interrupt again on rejection (replan loop); we mark
    the row appropriately and let the caller poll.
    """
    decision = decision.lower()
    if decision not in ("approve", "reject"):
        raise ValueError(f"bad decision: {decision!r}")

    resume_payload: Dict[str, Any] = {"decision": decision}
    if overrides:
        resume_payload["overrides"] = dict(overrides)
    if reason:
        resume_payload["reason"] = reason

    config: Dict[str, Any] = {"configurable": {"thread_id": agent_run_id}}
    audit_holder: Dict[str, Optional[str]] = {"id": agent_run_id}

    # Look up the mission_id off the agent_runs row so finalize_succeeded
    # can write rankings against the right mission.
    factory = get_session_factory()
    async with factory() as session:
        from app.models.agent_run import AgentRun

        run = await session.get(AgentRun, agent_run_id)
        if run is None:
            raise ValueError(f"agent_run {agent_run_id} not found")
        mission_id = run.mission_id
        # Flip status back to running for the resumed phase so observers
        # see "running" instead of stale "interrupted".
        run.status = "running"
        await session.commit()

    async def _drive_resume() -> None:
        try:
            async with AsyncSqliteSaver.from_conn_string(_checkpoint_path()) as saver:
                graph = build_graph(audit_run_id_holder=audit_holder, checkpointer=saver)
                result = await graph.ainvoke(Command(resume=resume_payload), config=config)

                interrupts = (
                    result.get("__interrupt__") if isinstance(result, dict) else None
                )
                if interrupts:
                    await end_run(
                        agent_run_id,
                        status="interrupted",
                        output_dict={"awaiting": "human_approval"},
                    )
                    return

                await _finalize_succeeded_run(
                    mission_id=mission_id,
                    agent_run_id=agent_run_id,
                    payload=result,
                )
        except Exception as exc:  # noqa: BLE001
            try:
                await end_run(
                    agent_run_id,
                    status="failed",
                    output_dict=None,
                    error=f"{type(exc).__name__}: {exc}",
                )
            except Exception:  # noqa: BLE001
                pass

    asyncio.create_task(_drive_resume())
    return "running"


async def get_run_status(agent_run_id: str) -> Optional[Tuple[str, Optional[str]]]:
    """Convenience: read just status + error for the given run id.

    Returns ``None`` if the row is missing.
    """
    from app.models.agent_run import AgentRun

    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(AgentRun, agent_run_id)
        if run is None:
            return None
        return run.status, run.error


__all__ = [
    "kick_recommend",
    "parse_only",
    "resume_with_decision",
    "get_run_status",
]
