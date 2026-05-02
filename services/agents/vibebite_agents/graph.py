"""LangGraph wiring for the `recommend_v1` C4-slice graph.

This is the C4 slice of the graph defined in implementation.md section 8.
On top of the C3 5-node linear chain it adds two new nodes
(``select_winner``, ``replan``), a dedicated ``await_approval`` HITL
gate that calls ``interrupt()``, and a conditional edge that loops the
graph back into ``score_candidates`` on rejection (capped at 3 replan
iterations to avoid runaway loops)::

    START
      -> parse_preferences
      -> search_places
      -> normalize_places
      -> score_candidates
      -> explain_candidates
      -> select_winner
      -> await_approval                # interrupts; resumed by the caller
           -> approve -> END
           -> reject  -> replan -> score_candidates -> ... -> await_approval

Persistence:
  * Each compiled graph captures a per-run audit context (the
    ``agent_run_id`` set on a shared mutable holder dict). The wrapper
    around each node times execution and writes one ``agent_run_steps``
    row per call -- the wrapper fires every iteration of the replan
    loop, so a 2-rejection demo writes more than 5 step rows.
  * ``begin_run`` / ``end_run`` are called by ``run_demo`` (or the API
    invocation path) -- they bracket the graph invocation so the run
    row is written even if the graph crashes.
  * For HITL we attach a ``langgraph.checkpoint.sqlite.AsyncSqliteSaver``
    so state survives between the interrupt and the resume call. The
    checkpointer writes its own ``checkpoints`` / ``writes`` tables that
    do not collide with the application schema.

Async-first
-----------
Nodes are registered as async functions; callers invoke the graph with
``await graph.ainvoke(state_dict, config=...)`` so a single asyncio
loop drives the entire run.

Python 3.9 / LangGraph schema note still applies: see ``GraphStateDict``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.config import var_child_runnable_config
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from typing_extensions import Literal, TypedDict

from .audit import record_step
from .nodes.explain_candidates import explain_candidates
from .nodes.normalize_places import normalize_places
from .nodes.parse_preferences import parse_preferences
from .nodes.replan import replan
from .nodes.score_candidates import score_candidates
from .nodes.search_places import search_places
from .nodes.select_winner import select_winner
from .state import CandidatePlace, GraphState, MemberPref


# Cap on rejection cycles before we force-approve to avoid an infinite
# replan loop. Surfaced as a module-level constant so run_demo and tests
# can reference it.
MAX_REPLAN_ITERATIONS = 3


class GraphStateDict(TypedDict, total=False):
    """Python 3.9-compatible TypedDict mirror of GraphState."""

    # inputs
    mission_id: UUID
    member_prefs: List[MemberPref]
    location: Tuple[float, float]
    search_radius_m: int
    # derived
    group_constraints: Optional[Dict[str, Any]]
    candidates: List[CandidatePlace]
    shortlist: List[CandidatePlace]
    # voting
    poll_id: Optional[UUID]
    votes: Dict[str, Dict[str, Any]]
    # decision
    winner: Optional[CandidatePlace]
    backup: Optional[CandidatePlace]
    # control
    needs_human_approval: bool
    approval_decision: Optional[Literal["approve", "reject"]]
    # observability
    agent_run_id: UUID


AsyncNode = Callable[[GraphState], Awaitable[Dict[str, Any]]]


def _input_snapshot(node_name: str, gs: GraphState) -> Dict[str, Any]:
    """Capture a small JSON-friendly view of the inputs each node reads."""
    if node_name == "parse_preferences":
        return {"member_pref_count": len(gs.member_prefs)}
    if node_name == "search_places":
        return {
            "group_constraints": gs.group_constraints,
            "location": list(gs.location),
            "search_radius_m": gs.search_radius_m,
        }
    if node_name == "normalize_places":
        return {"candidate_count": len(gs.candidates)}
    if node_name == "score_candidates":
        return {"candidate_count": len(gs.candidates)}
    if node_name == "explain_candidates":
        return {"candidate_count": len(gs.candidates)}
    if node_name == "select_winner":
        return {"shortlist_size": len(gs.shortlist)}
    if node_name == "replan":
        gc = gs.group_constraints or {}
        return {
            "replan_reason": gc.get("_replan_reason"),
            "replan_overrides": gc.get("_replan_overrides"),
        }
    if node_name == "await_approval":
        winner = gs.winner
        return {
            "winner_name": getattr(winner, "name", None),
            "winner_score": getattr(winner, "score", None),
        }
    return {}


def _output_snapshot(node_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Capture a small JSON-friendly view of each node's emitted update."""
    out: Dict[str, Any] = {}
    if "group_constraints" in result:
        out["group_constraints"] = result["group_constraints"]
    if "candidates" in result:
        cands = result["candidates"]
        out["candidate_count"] = len(cands)
        out["top5"] = [
            {"name": c.name, "score": c.score, "place_id": str(c.place_id)}
            for c in cands[:5]
        ]
    if "shortlist" in result:
        sl = result["shortlist"]
        out["shortlist"] = [
            {
                "name": c.name,
                "score": c.score,
                "place_id": str(c.place_id),
                "pros": list(c.pros),
                "cons": list(c.cons),
            }
            for c in sl
        ]
    if "winner" in result:
        w = result["winner"]
        out["winner"] = (
            {"name": w.name, "score": w.score, "place_id": str(w.place_id)}
            if w is not None
            else None
        )
    if "backup" in result:
        b = result["backup"]
        out["backup"] = (
            {"name": b.name, "score": b.score, "place_id": str(b.place_id)}
            if b is not None
            else None
        )
    if "approval_decision" in result:
        out["approval_decision"] = result["approval_decision"]
    if "needs_human_approval" in result:
        out["needs_human_approval"] = result["needs_human_approval"]
    return out


def _wrap(
    node: AsyncNode,
    *,
    audit_run_id_holder: Dict[str, Optional[str]],
) -> Callable[[GraphStateDict], Awaitable[Dict[str, Any]]]:
    """Async wrapper: rebuilds GraphState and records a step row per call.

    Note: the runner accepts ``config`` as a kwarg so we can manually set
    LangGraph's ``var_child_runnable_config`` contextvar before delegating
    to the underlying node. This is required for ``interrupt()`` to work
    on Python 3.9, where ``asyncio.create_task`` cannot accept a context
    arg and so LangGraph cannot propagate the contextvar itself.
    """

    node_name = node.__name__

    async def runner(state: GraphStateDict, config: RunnableConfig) -> Dict[str, Any]:
        gs = GraphState.model_validate(dict(state))
        run_id = audit_run_id_holder.get("id")
        started_at = datetime.now(timezone.utc)
        # Manually wire up the contextvar so interrupt() works on Python 3.9.
        token = var_child_runnable_config.set(config)
        try:
            try:
                result = await node(gs) or {}
            except Exception as exc:
                latency_ms = int(
                    (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
                )
                # GraphInterrupt is a control-flow exception used by
                # interrupt(); don't record it as a "failed" step. Match
                # by name so we don't have to import the private symbol.
                if type(exc).__name__ == "GraphInterrupt":
                    raise
                if run_id:
                    try:
                        await record_step(
                            agent_run_id=run_id,
                            node_name=node_name,
                            started_at=started_at,
                            status="failed",
                            input_dict=_input_snapshot(node_name, gs),
                            output_dict=None,
                            latency_ms=latency_ms,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    except Exception:  # noqa: BLE001
                        pass
                raise
            latency_ms = int(
                (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
            )
            if run_id:
                try:
                    await record_step(
                        agent_run_id=run_id,
                        node_name=node_name,
                        started_at=started_at,
                        status="succeeded",
                        input_dict=_input_snapshot(node_name, gs),
                        output_dict=_output_snapshot(node_name, result),
                        latency_ms=latency_ms,
                        error=None,
                    )
                except Exception:  # noqa: BLE001
                    pass
            return result
        finally:
            var_child_runnable_config.reset(token)

    runner.__name__ = node_name
    return runner


# ---- HITL gate -----------------------------------------------------------
#
# ``await_approval`` is a tiny gate node that calls ``interrupt()`` with
# the proposed winner so the human (CLI for now, REST API later) can
# inspect it. The graph pauses; on resume the caller passes back a
# ``Command(resume={"decision": "approve"|"reject", ...})`` and that
# resume payload is what ``interrupt()`` returns inside this function.
#
# The audit-step row for this node is written by ``_wrap`` only AFTER
# resume completes (because before resume the function never returns).
# That is the desired behaviour -- the step row's latency_ms then
# represents the *time spent waiting for the human*, which is useful.
async def await_approval(state: GraphState) -> Dict[str, Any]:
    """Pause the graph for human approval; return the approval decision."""
    winner = state.winner
    backup = state.backup

    # Track how many times we've already looped; cap at MAX_REPLAN_ITERATIONS.
    constraints = dict(state.group_constraints or {})
    iteration = int(constraints.get("_replan_iteration", 0))

    # If we've already replanned the maximum number of times, we force
    # an approval so the graph cannot loop forever. The audit row will
    # show the forced decision.
    if iteration >= MAX_REPLAN_ITERATIONS:
        return {
            "approval_decision": "approve",
            "needs_human_approval": False,
            "group_constraints": constraints,
        }

    payload = {
        "winner": (
            {
                "name": winner.name,
                "score": winner.score,
                "place_id": str(winner.place_id),
                "pros": list(winner.pros),
                "cons": list(winner.cons),
            }
            if winner is not None
            else None
        ),
        "backup": (
            {
                "name": backup.name,
                "score": backup.score,
                "place_id": str(backup.place_id),
            }
            if backup is not None
            else None
        ),
        "iteration": iteration,
    }

    # interrupt() returns the value supplied via Command(resume=...).
    resume_value = interrupt(payload)

    # Normalize: resume_value can be a dict or a bare string per call site.
    decision: str
    overrides: Dict[str, Any] = {}
    reason: Optional[str] = None
    if isinstance(resume_value, dict):
        decision = str(resume_value.get("decision", "approve")).lower()
        overrides = dict(resume_value.get("overrides") or {})
        reason = resume_value.get("reason")
    else:
        decision = str(resume_value).lower()

    if decision not in ("approve", "reject"):
        decision = "approve"

    if decision == "reject":
        constraints["_replan_reason"] = reason or "rejected by human"
        constraints["_replan_overrides"] = overrides
        constraints["_replan_iteration"] = iteration + 1
        return {
            "approval_decision": "reject",
            "needs_human_approval": True,
            "group_constraints": constraints,
        }

    # Approve path: clear any leftover replan sentinels.
    for k in ("_replan_reason", "_replan_overrides"):
        constraints.pop(k, None)
    return {
        "approval_decision": "approve",
        "needs_human_approval": False,
        "group_constraints": constraints,
    }


def _route_after_approval(state: GraphStateDict) -> str:
    """Conditional edge keyed on ``state.approval_decision``."""
    decision = state.get("approval_decision") if isinstance(state, dict) else None
    if decision == "reject":
        return "replan"
    return END


def build_graph(
    *,
    audit_run_id_holder: Optional[Dict[str, Optional[str]]] = None,
    checkpointer: Optional[Any] = None,
):
    """Build and compile the C4-slice ``recommend_v1`` LangGraph.

    Parameters
    ----------
    audit_run_id_holder:
        Optional ``{"id": <agent_run_id> | None}`` shared mutable map.
        When set, each node records an ``agent_run_steps`` row tagged
        with the active run id. ``run_demo`` populates this between
        ``begin_run`` and ``ainvoke`` so every invocation -- including
        replan-loop re-runs of ``score_candidates`` / ``explain_candidates``
        / ``select_winner`` -- is captured.
        When ``None`` or empty, audit recording is silently skipped
        (used by ``--no-db`` mode and offline tests).
    checkpointer:
        Optional LangGraph checkpointer used for HITL state persistence.
        Required if you want to resume from an ``interrupt()``; pass an
        ``AsyncSqliteSaver`` instance (see ``run_demo`` for the canonical
        wiring against ``services/api/vibebite.db``).
    """
    holder = audit_run_id_holder if audit_run_id_holder is not None else {"id": None}

    builder: StateGraph = StateGraph(GraphStateDict)

    builder.add_node("parse_preferences", _wrap(parse_preferences, audit_run_id_holder=holder))
    builder.add_node("search_places", _wrap(search_places, audit_run_id_holder=holder))
    builder.add_node("normalize_places", _wrap(normalize_places, audit_run_id_holder=holder))
    builder.add_node("score_candidates", _wrap(score_candidates, audit_run_id_holder=holder))
    builder.add_node("explain_candidates", _wrap(explain_candidates, audit_run_id_holder=holder))
    builder.add_node("select_winner", _wrap(select_winner, audit_run_id_holder=holder))
    builder.add_node("await_approval", _wrap(await_approval, audit_run_id_holder=holder))
    builder.add_node("replan", _wrap(replan, audit_run_id_holder=holder))

    builder.add_edge(START, "parse_preferences")
    builder.add_edge("parse_preferences", "search_places")
    builder.add_edge("search_places", "normalize_places")
    builder.add_edge("normalize_places", "score_candidates")
    builder.add_edge("score_candidates", "explain_candidates")
    builder.add_edge("explain_candidates", "select_winner")
    builder.add_edge("select_winner", "await_approval")

    builder.add_conditional_edges(
        "await_approval",
        _route_after_approval,
        {"replan": "replan", END: END},
    )

    # On rejection the replan node updates the constraints, then we
    # bounce back into score_candidates (NOT search -- we keep the
    # candidate set, just rescore against the new bar).
    builder.add_edge("replan", "score_candidates")

    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


__all__ = ["build_graph", "GraphStateDict", "MAX_REPLAN_ITERATIONS"]
