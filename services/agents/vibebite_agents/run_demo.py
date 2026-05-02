"""CLI demo runner for the C3-slice LangGraph.

Loads the canonical 5-member fixture mission, runs the full graph
(``parse_preferences`` -> ``search_places`` -> ``normalize_places`` ->
``score_candidates`` -> ``explain_candidates``), persists every step to
SQLite, and pretty-prints the merged group constraints, the top-5
ranked candidates, and a summary of the agent_run row.

Usage::

    python -m vibebite_agents.run_demo            # one-shot run, full DB persistence
    python -m vibebite_agents.run_demo --no-db    # skip DB writes (offline mode)
    python -m vibebite_agents.run_demo --verbose  # dump full state per step

Exits 0 on success, non-zero on any unhandled exception.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

# Load repo-root .env BEFORE importing modules that read GEMINI_API_KEY etc.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .fixtures.sample_mission import sample_mission_state
from .graph import build_graph
from .state import CandidatePlace, GraphState

# Static fixture-derived ids used by the seeded mission row in the API DB.
_SEED_MISSION_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _coerce_state(raw: Any) -> GraphState:
    if isinstance(raw, GraphState):
        return raw
    if isinstance(raw, dict):
        return GraphState.model_validate(raw)
    try:
        return GraphState.model_validate(dict(raw))
    except Exception:
        return raw  # type: ignore[return-value]


def _pretty_print_constraints(console: Console, constraints: dict | None) -> None:
    if not constraints:
        console.print(Panel("[yellow](no merged group_constraints produced)[/yellow]",
                            title="Merged group constraints"))
        return
    body = json.dumps(constraints, indent=2, sort_keys=True, default=str)
    console.print(Panel(body, title="Merged group constraints", expand=False))


def _pretty_print_top5(console: Console, candidates: list[CandidatePlace]) -> None:
    ranked = sorted(
        candidates,
        key=lambda c: (c.score is None, -(c.score or 0.0)),
    )[:5]

    table = Table(title="Top 5 candidates", show_lines=True)
    table.add_column("#", justify="right", style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Pros", style="green")
    table.add_column("Cons", style="red")

    if not ranked:
        console.print(Panel("[yellow](no candidates produced)[/yellow]", title="Top 5 candidates"))
        return

    for i, cand in enumerate(ranked, start=1):
        score_s = f"{cand.score:.2f}" if cand.score is not None else "-"
        pros = "\n".join(f"- {p}" for p in cand.pros[:2]) or "-"
        cons = "\n".join(f"- {c}" for c in cand.cons[:1]) or "-"
        table.add_row(str(i), cand.name, score_s, pros, cons)

    console.print(table)


def _dump_step(console: Console, step_idx: int, payload: Any) -> None:
    try:
        as_dict = payload if isinstance(payload, dict) else dict(payload)
    except Exception:
        as_dict = {"_raw": repr(payload)}

    for node_name, value in as_dict.items():
        try:
            body = json.dumps(value, indent=2, default=str, sort_keys=True)
        except Exception:
            body = repr(value)
        console.print(Panel(body, title=f"step {step_idx}: {node_name}", expand=False))


async def _print_run_summary(console: Console, agent_run_id: str) -> None:
    """Read the just-finished agent_run + steps + rankings out of the DB."""
    from sqlalchemy import select

    from .db import get_async_session_factory
    from app.models import AgentRun, AgentRunStep, Place, Ranking

    factory = get_async_session_factory()
    async with factory() as session:
        run = await session.get(AgentRun, agent_run_id)
        steps = (
            await session.execute(
                select(AgentRunStep)
                .where(AgentRunStep.agent_run_id == agent_run_id)
                .order_by(AgentRunStep.started_at)
            )
        ).scalars().all()
        rankings = (
            await session.execute(
                select(Ranking, Place)
                .join(Place, Ranking.place_id == Place.id)
                .where(Ranking.agent_run_id == agent_run_id)
                .order_by(Ranking.rank)
            )
        ).all()

    if run is None:
        console.print("[red]agent_run row not found![/red]")
        return

    duration_ms: int | None = None
    if run.started_at and run.finished_at:
        duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

    summary_lines = [
        f"run id:      {run.id}",
        f"graph:       {run.graph_name}",
        f"trigger:     {run.trigger}",
        f"status:      {run.status}",
        f"duration:    {duration_ms} ms" if duration_ms is not None else "duration:    n/a",
        f"step count:  {len(steps)}",
    ]
    console.print(Panel("\n".join(summary_lines), title="agent_run summary", expand=False))

    step_table = Table(title="agent_run_steps", show_lines=False)
    step_table.add_column("#", justify="right")
    step_table.add_column("node")
    step_table.add_column("status")
    step_table.add_column("latency (ms)", justify="right")
    for i, st in enumerate(steps, start=1):
        step_table.add_row(
            str(i), st.node_name, st.status, str(st.latency_ms) if st.latency_ms is not None else "-"
        )
    console.print(step_table)

    rank_table = Table(title="rankings (DB)", show_lines=False)
    rank_table.add_column("rank", justify="right")
    rank_table.add_column("place")
    rank_table.add_column("score", justify="right")
    for ranking, place in rankings:
        rank_table.add_row(str(ranking.rank), place.name, f"{float(ranking.score):.2f}")
    console.print(rank_table)


async def _async_main(args: argparse.Namespace) -> int:
    console = Console()
    console.print(
        "[bold]VibeBite C3 demo[/bold] — building graph and loading fixture mission..."
    )

    initial_state = sample_mission_state()
    initial_state_dict = initial_state.model_dump()

    audit_holder: dict[str, str | None] = {"id": None}
    graph = build_graph(audit_run_id_holder=audit_holder)

    agent_run_id: str | None = None
    if not args.no_db:
        from .audit import begin_run, end_run, write_rankings

        try:
            agent_run_id = await begin_run(
                mission_id=_SEED_MISSION_ID,
                graph_name="recommend_v1",
                trigger="cli_demo",
                input_dict={
                    "mission_id": str(initial_state.mission_id),
                    "location": list(initial_state.location),
                    "search_radius_m": initial_state.search_radius_m,
                    "member_pref_count": len(initial_state.member_prefs),
                },
            )
            audit_holder["id"] = agent_run_id
            console.print(f"[dim]begin_run -> agent_run_id={agent_run_id}[/dim]")
        except Exception as exc:  # noqa: BLE001
            console.print(
                f"[yellow]warn: begin_run failed ({exc!r}); continuing without DB audit.[/yellow]"
            )
            agent_run_id = None
            audit_holder["id"] = None

    final_payload: Any
    error_str: str | None = None
    try:
        if args.verbose:
            console.print("[dim]Streaming node updates (verbose mode)...[/dim]\n")
            i = 0
            async for chunk in graph.astream(initial_state_dict, stream_mode="updates"):
                i += 1
                _dump_step(console, i, chunk)
            final_payload = await graph.ainvoke(initial_state_dict)
        else:
            final_payload = await graph.ainvoke(initial_state_dict)
    except Exception as exc:
        error_str = f"{type(exc).__name__}: {exc}"
        if agent_run_id:
            try:
                from .audit import end_run
                await end_run(agent_run_id, status="failed", output_dict=None, error=error_str)
            except Exception:  # noqa: BLE001
                pass
        raise

    final_state = _coerce_state(final_payload)
    if isinstance(final_state, GraphState):
        constraints = final_state.group_constraints
        candidates = final_state.candidates
        shortlist = final_state.shortlist
    else:
        constraints = final_payload.get("group_constraints") if isinstance(final_payload, dict) else None
        raw_cands = final_payload.get("candidates", []) if isinstance(final_payload, dict) else []
        candidates = [
            c if isinstance(c, CandidatePlace) else CandidatePlace.model_validate(c)
            for c in raw_cands
        ]
        raw_short = final_payload.get("shortlist", []) if isinstance(final_payload, dict) else []
        shortlist = [
            c if isinstance(c, CandidatePlace) else CandidatePlace.model_validate(c)
            for c in raw_short
        ]

    if agent_run_id and not args.no_db:
        from .audit import end_run, write_rankings

        # Top-5 = the explained shortlist (or fall back to scored candidates).
        top5 = shortlist if shortlist else candidates[:5]
        try:
            await write_rankings(
                mission_id=_SEED_MISSION_ID,
                agent_run_id=agent_run_id,
                ranked_candidates=top5,
            )
        except Exception as exc:  # noqa: BLE001
            console.print(f"[yellow]warn: write_rankings failed: {exc!r}[/yellow]")

        try:
            await end_run(
                agent_run_id,
                status="succeeded",
                output_dict={
                    "candidate_count": len(candidates),
                    "shortlist_size": len(shortlist),
                },
            )
        except Exception as exc:  # noqa: BLE001
            console.print(f"[yellow]warn: end_run failed: {exc!r}[/yellow]")

    console.print()
    _pretty_print_constraints(console, constraints)
    console.print()
    _pretty_print_top5(console, shortlist or candidates)

    if agent_run_id and not args.no_db:
        console.print()
        try:
            await _print_run_summary(console, agent_run_id)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[yellow]warn: failed to print run summary: {exc!r}[/yellow]")

    console.print("\n[bold green]Done.[/bold green]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the C3-slice VibeBite recommend graph.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Dump the full state diff after every node executes.",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Run in offline mode — no DB reads/writes (uses in-memory state only).",
    )
    args = parser.parse_args(argv)

    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
