"""Audit-trail helpers — agent_runs, agent_run_steps, rankings.

Every graph invocation gets an ``agent_runs`` row. Every node execution
gets an ``agent_run_steps`` row. The top-5 ranked candidates get
``rankings`` rows with ``reasons={pros:[], cons:[]}`` so downstream UIs
can show *why* each place ranked.

All helpers open their own short-lived session — that keeps step writes
durable even if a later node fails (the orchestrator can still see
"step X succeeded; step Y failed").
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(obj: Any, depth: int = 0) -> Any:
    """Best-effort JSON-safe scrub. Trims big raw_blob payloads, etc."""
    if depth > 6:
        return "<…depth-trimmed…>"
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    # Pydantic models / similar
    if hasattr(obj, "model_dump"):
        try:
            return _json_safe(obj.model_dump(), depth + 1)
        except Exception:  # noqa: BLE001
            return repr(obj)
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k)
            if key == "raw_blob":
                # Drop the bulky blob — it's already in the places table.
                out[key] = "<omitted>"
                continue
            out[key] = _json_safe(v, depth + 1)
        return out
    if isinstance(obj, (list, tuple, set)):
        return [_json_safe(x, depth + 1) for x in obj]
    # Last-resort: str() for UUIDs, datetimes, etc.
    try:
        json.dumps(obj)
        return obj
    except Exception:  # noqa: BLE001
        return str(obj)


# ----- the helpers themselves ---------------------------------------------

# Late imports inside fns avoid hammering app.* imports at module-load time.

async def begin_run(
    mission_id: str,
    graph_name: str,
    trigger: str,
    input_dict: dict[str, Any],
) -> str:
    from app.models import AgentRun

    from .db import get_async_session_factory as _factory_fn

    factory = _factory_fn()
    async with factory() as session:
        run = AgentRun(
            mission_id=mission_id,
            graph_name=graph_name,
            status="running",
            trigger=trigger,
            input=_json_safe(input_dict),
            started_at=_utcnow(),
        )
        session.add(run)
        await session.flush()
        run_id = run.id
        await session.commit()
    return run_id


async def end_run(
    agent_run_id: str,
    status: str,
    output_dict: Optional[dict[str, Any]],
    error: Optional[str] = None,
) -> None:
    from app.models import AgentRun

    from .db import get_async_session_factory as _factory_fn

    factory = _factory_fn()
    async with factory() as session:
        run = await session.get(AgentRun, agent_run_id)
        if run is None:
            return
        run.status = status
        run.finished_at = _utcnow()
        run.output = _json_safe(output_dict) if output_dict is not None else None
        run.error = error
        await session.commit()


async def record_step(
    agent_run_id: str,
    node_name: str,
    started_at: datetime,
    status: str,
    input_dict: Optional[dict[str, Any]],
    output_dict: Optional[dict[str, Any]],
    latency_ms: int,
    error: Optional[str] = None,
) -> None:
    from app.models import AgentRunStep

    from .db import get_async_session_factory as _factory_fn

    factory = _factory_fn()
    async with factory() as session:
        step = AgentRunStep(
            agent_run_id=agent_run_id,
            node_name=node_name,
            status=status,
            input=_json_safe(input_dict) if input_dict is not None else None,
            output=_json_safe(output_dict) if output_dict is not None else None,
            error=error,
            latency_ms=latency_ms,
            started_at=started_at,
            finished_at=_utcnow(),
        )
        session.add(step)
        await session.commit()


async def write_rankings(
    mission_id: str,
    agent_run_id: str,
    ranked_candidates: list[Any],
    *,
    top_n: int = 5,
) -> None:
    """Insert ranking rows for the top-N candidates."""
    from app.models import Ranking

    from .db import get_async_session_factory as _factory_fn

    factory = _factory_fn()
    async with factory() as session:
        for rank, cand in enumerate(ranked_candidates[:top_n], start=1):
            session.add(
                Ranking(
                    mission_id=mission_id,
                    place_id=str(cand.place_id),
                    agent_run_id=agent_run_id,
                    rank=rank,
                    score=float(cand.score) if cand.score is not None else 0.0,
                    reasons={"pros": list(cand.pros), "cons": list(cand.cons)},
                )
            )
        await session.commit()


__all__ = [
    "begin_run",
    "end_run",
    "record_step",
    "write_rankings",
]
