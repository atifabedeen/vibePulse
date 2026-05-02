"""LangGraph wiring for the `recommend_v1` C3-slice graph.

This is the C3 slice of the graph defined in implementation.md section 8.
It wires five nodes — `parse_preferences`, `search_places`,
`normalize_places`, `score_candidates`, and `explain_candidates` — into
a linear StateGraph::

    START -> parse_preferences -> search_places -> normalize_places ->
    score_candidates -> explain_candidates -> END

Persistence:
  * Each compiled graph captures a per-run audit context (the
    ``agent_run_id`` set on a shared mutable holder dict). The wrapper
    around each node times execution and writes one ``agent_run_steps``
    row per node.
  * ``begin_run`` / ``end_run`` are called by ``run_demo`` (or the API
    invocation path) — they bracket the graph invocation so the run
    row is written even if the graph crashes.

Async-first
-----------
Nodes are registered as async functions; callers invoke the graph with
``await graph.ainvoke(state_dict)`` so a single asyncio loop drives the
entire run. This avoids the multi-loop trap that would arise if each
node called ``asyncio.run`` while sharing a SQLAlchemy engine.

Python 3.9 / LangGraph schema note still applies: see ``GraphStateDict``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from typing_extensions import Literal, TypedDict

from .audit import record_step
from .nodes.explain_candidates import explain_candidates
from .nodes.normalize_places import normalize_places
from .nodes.parse_preferences import parse_preferences
from .nodes.score_candidates import score_candidates
from .nodes.search_places import search_places
from .state import CandidatePlace, GraphState, MemberPref


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
    return out


def _wrap(
    node: AsyncNode,
    *,
    audit_run_id_holder: Dict[str, Optional[str]],
) -> Callable[[GraphStateDict], Awaitable[Dict[str, Any]]]:
    """Async wrapper: rebuilds GraphState and records a step row per call."""

    node_name = node.__name__

    async def runner(state: GraphStateDict) -> Dict[str, Any]:
        gs = GraphState.model_validate(dict(state))
        run_id = audit_run_id_holder.get("id")
        started_at = datetime.now(timezone.utc)
        try:
            result = await node(gs) or {}
        except Exception as exc:
            latency_ms = int(
                (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
            )
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

    runner.__name__ = node_name
    return runner


def build_graph(
    *, audit_run_id_holder: Optional[Dict[str, Optional[str]]] = None
):
    """Build and compile the C3-slice ``recommend_v1`` LangGraph.

    Parameters
    ----------
    audit_run_id_holder:
        Optional ``{"id": <agent_run_id> | None}`` shared mutable map.
        When set, each node records an ``agent_run_steps`` row tagged
        with the active run id. ``run_demo`` populates this between
        ``begin_run`` and ``ainvoke`` so all five nodes are captured.
        When ``None`` or empty, audit recording is silently skipped
        (used by ``--no-db`` mode and offline tests).
    """
    holder = audit_run_id_holder if audit_run_id_holder is not None else {"id": None}

    builder: StateGraph = StateGraph(GraphStateDict)

    builder.add_node("parse_preferences", _wrap(parse_preferences, audit_run_id_holder=holder))
    builder.add_node("search_places", _wrap(search_places, audit_run_id_holder=holder))
    builder.add_node("normalize_places", _wrap(normalize_places, audit_run_id_holder=holder))
    builder.add_node("score_candidates", _wrap(score_candidates, audit_run_id_holder=holder))
    builder.add_node("explain_candidates", _wrap(explain_candidates, audit_run_id_holder=holder))

    builder.add_edge(START, "parse_preferences")
    builder.add_edge("parse_preferences", "search_places")
    builder.add_edge("search_places", "normalize_places")
    builder.add_edge("normalize_places", "score_candidates")
    builder.add_edge("score_candidates", "explain_candidates")
    builder.add_edge("explain_candidates", END)

    return builder.compile()


__all__ = ["build_graph", "GraphStateDict"]
