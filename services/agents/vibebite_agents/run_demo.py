"""CLI demo runner for the C4-slice LangGraph.

Loads the canonical 5-member fixture mission, runs the full graph
(``parse_preferences`` -> ``search_places`` -> ``normalize_places`` ->
``score_candidates`` -> ``explain_candidates`` -> ``select_winner`` ->
[HITL gate]), persists every step to SQLite, and pretty-prints the
merged group constraints, the top-5 ranked candidates, the proposed
winner each iteration, and a summary of the agent_run row.

The HITL gate uses LangGraph's ``interrupt()`` / ``Command(resume=...)``
loop. By default, the demo auto-approves the first proposed winner.
``--reject`` simulates one rejection (looser budget) then approve;
``--reject-twice`` rejects twice and accepts the third proposal; the
graph caps replan loops at 3 iterations and force-approves after that.

Usage::

    python -m vibebite_agents.run_demo
    python -m vibebite_agents.run_demo --reject
    python -m vibebite_agents.run_demo --reject-twice
    python -m vibebite_agents.run_demo --no-db
    python -m vibebite_agents.run_demo --verbose

Exits 0 on success, non-zero on any unhandled exception.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any
from uuid import uuid4

# Load repo-root .env BEFORE importing modules that read GEMINI_API_KEY etc.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .fixtures.sample_mission import sample_mission_state
from .graph import MAX_REPLAN_ITERATIONS, build_graph
from .state import CandidatePlace, GraphState

# Static fixture-derived ids used by the seeded mission row in the API DB.
_SEED_MISSION_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

# The SQLite file the API service already uses; the LangGraph checkpointer
# creates its own ``checkpoints``/``writes`` tables that don't collide.
_DEFAULT_CHECKPOINT_DB = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "..",
    "api",
    "vibebite.db",
)


def _coerce_state(raw: Any) -> Any:
    if isinstance(raw, GraphState):
        return raw
    if isinstance(raw, dict):
        try:
            return GraphState.model_validate(raw)
        except Exception:
            return raw
    try:
        return GraphState.model_validate(dict(raw))
    except Exception:
        return raw


def _pretty_print_constraints(console: Console, constraints: dict | None) -> None:
    if not constraints:
        console.print(Panel("[yellow](no merged group_constraints produced)[/yellow]",
                            title="Merged group constraints"))
        return
    # Hide the internal _replan_iteration counter from the user view.
    view = {k: v for k, v in constraints.items() if not k.startswith("_replan_")}
    body = json.dumps(view, indent=2, sort_keys=True, default=str)
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
                .order_by(Ranking.created_at.desc(), Ranking.rank)
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

    rank_table = Table(title="rankings (DB; all iterations)", show_lines=False)
    rank_table.add_column("rank", justify="right")
    rank_table.add_column("place")
    rank_table.add_column("score", justify="right")
    rank_table.add_column("created_at")
    # Show every ranking row tagged with this run; iteration boundaries
    # are visible in the created_at column so the human can trust the
    # sequence (each batch shares a near-identical timestamp).
    for ranking, place in rankings:
        rank_table.add_row(
            str(ranking.rank),
            place.name,
            f"{float(ranking.score):.2f}",
            ranking.created_at.strftime("%H:%M:%S.%f")[:-3] if ranking.created_at else "-",
        )
    console.print(rank_table)


def _decision_for_iteration(args: argparse.Namespace, iteration: int) -> dict[str, Any]:
    """Return the simulated user resume payload for the given iteration index.

    Iteration 0 is the FIRST proposed winner. ``--reject`` rejects only on
    iteration 0; ``--reject-twice`` rejects on iterations 0 and 1.
    """
    if args.reject_twice and iteration < 2:
        return {
            "decision": "reject",
            "reason": (
                "user wants something cheaper (1st reject)"
                if iteration == 0
                else "still too pricey (2nd reject)"
            ),
            "overrides": {
                "budget_max_cents": 1500 if iteration == 0 else 1000,
            },
        }
    if args.reject and iteration == 0:
        return {
            "decision": "reject",
            "reason": "user wants something cheaper",
            "overrides": {"budget_max_cents": 1000},
        }
    return {"decision": "approve"}


async def _run_with_hitl(
    console: Console,
    args: argparse.Namespace,
    audit_holder: dict[str, str | None],
    initial_state_dict: dict[str, Any],
) -> tuple[Any, list[dict[str, Any]]]:
    """Drive the graph through interrupt/resume cycles until END or cap.

    Returns ``(final_payload, iteration_log)``. ``iteration_log`` is a list
    of dicts (one per HITL gate hit) with the proposed winner and the
    user's decision -- used for the post-run summary print.
    """
    iteration_log: list[dict[str, Any]] = []

    # Use AsyncSqliteSaver (LangGraph 0.6's async ctx-manager API).
    async with AsyncSqliteSaver.from_conn_string(_DEFAULT_CHECKPOINT_DB) as saver:
        graph = build_graph(audit_run_id_holder=audit_holder, checkpointer=saver)

        # A unique thread_id per demo run so checkpoints don't collide
        # across repeated invocations.
        thread_id = str(uuid4())
        config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

        # First pass: kick off until the first interrupt or terminal end.
        result = await graph.ainvoke(initial_state_dict, config=config)

        iteration = 0
        while True:
            # Detect interrupt: LangGraph 0.6 surfaces interrupts via the
            # ``__interrupt__`` key on the streamed/returned state dict.
            interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
            if not interrupts:
                # Graph reached END (or there was nothing to interrupt on).
                return result, iteration_log

            # Inspect the first interrupt's payload (we only have one HITL
            # gate node so there's always exactly one).
            try:
                ev = interrupts[0]
                payload = getattr(ev, "value", None) or {}
            except Exception:  # noqa: BLE001
                payload = {}

            proposed = payload.get("winner") if isinstance(payload, dict) else None
            iter_idx = payload.get("iteration", iteration) if isinstance(payload, dict) else iteration

            console.print()
            console.print(
                Panel(
                    json.dumps(proposed, indent=2, default=str) if proposed else "(none)",
                    title=f"HITL gate (iteration {iter_idx + 1}) -- proposed winner",
                    expand=False,
                )
            )

            if iter_idx >= MAX_REPLAN_ITERATIONS:
                # Should already have been auto-approved inside await_approval,
                # but be defensive.
                decision = {"decision": "approve"}
                console.print("[yellow]Replan cap reached -- auto-approving.[/yellow]")
            else:
                decision = _decision_for_iteration(args, iter_idx)
                console.print(
                    f"[bold]simulated decision:[/bold] {decision['decision']}"
                    + (f"  (reason: {decision.get('reason')})" if decision.get("reason") else "")
                )

            iteration_log.append(
                {
                    "iteration": iter_idx + 1,
                    "proposed_winner": proposed,
                    "decision": decision["decision"],
                    "reason": decision.get("reason"),
                    "overrides": decision.get("overrides"),
                }
            )

            # Optionally write a fresh batch of rankings rows for THIS
            # proposal so the audit trail records every iteration's top-5.
            if audit_holder.get("id") and not args.no_db:
                try:
                    from .audit import write_rankings

                    snap = await graph.aget_state(config)
                    cur_state = snap.values if snap is not None else {}
                    shortlist = cur_state.get("shortlist") or []
                    if shortlist:
                        coerced = [
                            c
                            if isinstance(c, CandidatePlace)
                            else CandidatePlace.model_validate(c)
                            for c in shortlist
                        ]
                        await write_rankings(
                            mission_id=_SEED_MISSION_ID,
                            agent_run_id=audit_holder["id"],
                            ranked_candidates=coerced,
                        )
                except Exception as exc:  # noqa: BLE001
                    console.print(
                        f"[yellow]warn: per-iteration write_rankings failed: {exc!r}[/yellow]"
                    )

            # Resume the graph with the user's decision.
            result = await graph.ainvoke(Command(resume=decision), config=config)
            iteration = iter_idx + 1


async def _async_main(args: argparse.Namespace) -> int:
    console = Console()
    console.print(
        "[bold]VibeBite C4 demo[/bold] -- building graph and loading fixture mission..."
    )

    initial_state = sample_mission_state()
    initial_state_dict = initial_state.model_dump()

    audit_holder: dict[str, str | None] = {"id": None}

    agent_run_id: str | None = None
    if not args.no_db:
        from .audit import begin_run

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
                    "mode": (
                        "reject_twice" if args.reject_twice
                        else "reject" if args.reject
                        else "auto_approve"
                    ),
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
    iteration_log: list[dict[str, Any]] = []
    try:
        final_payload, iteration_log = await _run_with_hitl(
            console, args, audit_holder, initial_state_dict
        )
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
        winner = final_state.winner
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
        raw_winner = final_payload.get("winner") if isinstance(final_payload, dict) else None
        if raw_winner is None:
            winner = None
        elif isinstance(raw_winner, CandidatePlace):
            winner = raw_winner
        else:
            try:
                winner = CandidatePlace.model_validate(raw_winner)
            except Exception:  # noqa: BLE001
                winner = None

    if agent_run_id and not args.no_db:
        from .audit import end_run, write_rankings

        # Final batch of rankings = the explained shortlist after the
        # last (approved) iteration. Per-iteration rankings were written
        # inside _run_with_hitl; this is the canonical "final" batch.
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
                    "iterations": len(iteration_log),
                    "final_winner": (
                        {"name": winner.name, "score": winner.score}
                        if winner is not None else None
                    ),
                },
            )
        except Exception as exc:  # noqa: BLE001
            console.print(f"[yellow]warn: end_run failed: {exc!r}[/yellow]")

    console.print()
    _pretty_print_constraints(console, constraints)
    console.print()
    _pretty_print_top5(console, shortlist or candidates)

    # Iteration history
    if iteration_log:
        hist = Table(title="HITL iteration history", show_lines=False)
        hist.add_column("iter", justify="right")
        hist.add_column("proposed winner")
        hist.add_column("decision")
        hist.add_column("reason")
        for entry in iteration_log:
            pw = entry.get("proposed_winner") or {}
            name = pw.get("name", "-") if isinstance(pw, dict) else "-"
            hist.add_row(
                str(entry["iteration"]),
                str(name),
                str(entry["decision"]),
                str(entry.get("reason") or "-"),
            )
        console.print()
        console.print(hist)

    if winner is not None:
        console.print()
        console.print(
            Panel(
                f"[bold cyan]{winner.name}[/bold cyan] (score {winner.score:.2f})",
                title="Final winner",
                expand=False,
            )
        )

    if agent_run_id and not args.no_db:
        console.print()
        try:
            await _print_run_summary(console, agent_run_id)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[yellow]warn: failed to print run summary: {exc!r}[/yellow]")

    console.print("\n[bold green]Done.[/bold green]")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the C4-slice VibeBite recommend graph.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Dump the full state diff after every node executes.",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Run in offline mode -- no DB reads/writes (uses in-memory state only).",
    )
    parser.add_argument(
        "--reject",
        "--reject-winner",
        dest="reject",
        action="store_true",
        help="Simulate rejecting the first proposed winner (loosens budget then approves).",
    )
    parser.add_argument(
        "--reject-twice",
        dest="reject_twice",
        action="store_true",
        help="Simulate two rejections in a row; auto-approves the third proposal.",
    )
    args = parser.parse_args(argv)

    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
