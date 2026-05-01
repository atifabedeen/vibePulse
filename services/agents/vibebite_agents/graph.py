"""LangGraph wiring for the `recommend_v1` C2-slice graph.

This is the C2 (offline) slice of the graph defined in implementation.md
section 8. It wires four nodes — `parse_preferences`, `search_places`,
`normalize_places`, and `score_candidates` — into a linear StateGraph::

    START -> parse_preferences -> search_places -> normalize_places ->
    score_candidates -> END

No checkpointer is used in C2; the graph runs in-memory only. Later
slices add `explain_candidates`, polling/voting nodes, and the Postgres
checkpointer for HITL resumption (see implementation.md sec 8.4).

Python 3.9 / LangGraph schema note
----------------------------------
LangGraph 0.6 builds its channel set by calling :func:`typing.get_type_hints`
on the state schema. On Python 3.9 the GraphState Pydantic model uses
PEP-604 `X | None` annotations (kept evaluable for Pydantic via
``from __future__ import annotations``), but the stdlib `get_type_hints`
still tries to evaluate them and raises ``TypeError: unsupported operand
type(s) for |``.

Per the task constraints we cannot modify ``state.py``, so we declare a
``TypedDict`` mirror with 3.9-compatible annotations and use it as the
schema. Each async node still expects a ``GraphState`` instance, so we
wrap them: the wrapper takes the dict LangGraph hands us, builds a
``GraphState``, awaits the node, and returns the partial-state dict.
This deviation is documented in implementation.md sec 8 fidelity terms
and should be revisited when the project moves to Python 3.10+.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from typing_extensions import Literal, TypedDict

from .nodes.normalize_places import normalize_places
from .nodes.parse_preferences import parse_preferences
from .nodes.score_candidates import score_candidates
from .nodes.search_places import search_places
from .state import CandidatePlace, GraphState, MemberPref


class GraphStateDict(TypedDict, total=False):
    """Python 3.9-compatible TypedDict mirror of GraphState.

    Field order and names match ``state.GraphState`` exactly so we can
    round-trip via ``GraphState(**state_dict)`` / ``model.model_dump()``.
    Keep this list in sync with ``state.py``.
    """

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


def _wrap(node: AsyncNode) -> Callable[[GraphStateDict], Dict[str, Any]]:
    """Adapt an async ``node(GraphState) -> dict`` to LangGraph's sync dict-in/dict-out contract.

    LangGraph passes whatever schema we declared to each node — for our
    TypedDict that's a plain dict. The C2 nodes were written against the
    Pydantic ``GraphState`` (so ``state.member_prefs`` etc. work), so we
    rebuild the model on the way in. The node returns a partial-state
    dict, which LangGraph merges into the channel state for us.
    """

    def runner(state: GraphStateDict) -> Dict[str, Any]:
        gs = GraphState.model_validate(dict(state))
        result = asyncio.run(node(gs))
        return result or {}

    runner.__name__ = node.__name__
    return runner


def build_graph():
    """Build and compile the C2-slice `recommend_v1` LangGraph.

    Returns the compiled graph. Callers invoke it with a state dict (or
    a ``GraphState`` instance, which we coerce). The graph has no
    checkpointer in C2 — state is in-memory only.
    """
    builder: StateGraph = StateGraph(GraphStateDict)

    builder.add_node("parse_preferences", _wrap(parse_preferences))
    builder.add_node("search_places", _wrap(search_places))
    builder.add_node("normalize_places", _wrap(normalize_places))
    builder.add_node("score_candidates", _wrap(score_candidates))

    builder.add_edge(START, "parse_preferences")
    builder.add_edge("parse_preferences", "search_places")
    builder.add_edge("search_places", "normalize_places")
    builder.add_edge("normalize_places", "score_candidates")
    builder.add_edge("score_candidates", END)

    return builder.compile()


__all__ = ["build_graph", "GraphStateDict"]
