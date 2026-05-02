"""`replan` LangGraph node.

Triggered when a human rejects the proposed winner at the HITL gate.
The rejection-side resume payload (carried via ``state.group_constraints``
because we cannot widen ``GraphState`` -- see C4 task notes) provides:

  * ``_replan_reason``    : short free-text description of *why* the
                            human is asking for a do-over.
  * ``_replan_overrides`` : dict of constraint keys to clobber on top
                            of the existing merged group_constraints
                            (e.g. ``{"budget_max_cents": 1000}``).

Logic
-----
1. Apply the overrides on top of ``state.group_constraints``.
2. Drop the ``_replan_*`` sentinels so the next pass starts clean and
   the loop cannot self-trigger.
3. Log the diff via structlog for the audit trail.

The graph routes this node back into ``score_candidates`` (NOT search --
we keep the same candidate set, just rescore against the new bar).
"""

from __future__ import annotations

from typing import Any

import structlog

from ..state import GraphState

_log = structlog.get_logger(__name__)


async def replan(state: GraphState) -> dict[str, Any]:
    """Apply replan overrides to group_constraints and strip the sentinels."""
    constraints = dict(state.group_constraints or {})

    reason = constraints.pop("_replan_reason", None)
    overrides = constraints.pop("_replan_overrides", None) or {}

    before = {k: constraints.get(k) for k in overrides.keys()} if overrides else {}

    if isinstance(overrides, dict):
        for key, value in overrides.items():
            constraints[key] = value

    try:
        _log.info(
            "replan_applied",
            reason=reason,
            before=before,
            after={k: constraints.get(k) for k in (overrides or {}).keys()},
        )
    except Exception:  # noqa: BLE001
        pass

    return {"group_constraints": constraints}


__all__ = ["replan"]
