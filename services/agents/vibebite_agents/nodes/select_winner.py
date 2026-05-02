"""`select_winner` LangGraph node.

Reads:
  * ``state.shortlist`` — top-5 from ``explain_candidates``
  * ``state.votes``     — empty in C4 (voting is the C5 REST API job).
                          C4 simply picks the highest-scored shortlist
                          entry as the proposed winner.

Writes:
  * ``state.winner``                 — the top shortlist entry
  * ``state.backup``                 — the runner-up (or ``None``)
  * ``state.needs_human_approval``   — ``True`` (the HITL gate awaits)

The actual ``interrupt()`` call lives in the dedicated ``await_approval``
gate node (see ``graph.py``) so that this node stays a pure state-update
function and the audit wrapper records its own step row before the graph
pauses for the human.
"""

from __future__ import annotations

from typing import Any

import structlog

from ..state import GraphState

_log = structlog.get_logger(__name__)


async def select_winner(state: GraphState) -> dict[str, Any]:
    """Pick the proposed winner + backup from the explained shortlist."""
    shortlist = list(state.shortlist or [])
    if not shortlist:
        # Nothing to propose; mark approval not needed so the graph can end.
        _log.warning("select_winner_empty_shortlist")
        return {
            "winner": None,
            "backup": None,
            "needs_human_approval": False,
        }

    winner = shortlist[0]
    backup = shortlist[1] if len(shortlist) > 1 else None

    try:
        _log.info(
            "select_winner_proposed",
            winner_name=winner.name,
            winner_score=winner.score,
            backup_name=getattr(backup, "name", None),
        )
    except Exception:  # noqa: BLE001
        pass

    return {
        "winner": winner,
        "backup": backup,
        "needs_human_approval": True,
        # Reset any prior decision so the conditional edge doesn't latch
        # on a stale "approve"/"reject" from the previous iteration.
        "approval_decision": None,
    }


__all__ = ["select_winner"]
