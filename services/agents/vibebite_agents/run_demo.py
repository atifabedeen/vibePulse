"""CLI demo runner for the C2-slice LangGraph.

Loads the canonical 5-member fixture mission, runs the full graph
(`parse_preferences` -> `search_places` -> `normalize_places` ->
`score_candidates`), and pretty-prints the merged group constraints plus
the top-5 ranked candidates.

Usage::

    python -m vibebite_agents.run_demo            # one-shot run
    python -m vibebite_agents.run_demo --verbose  # dump full state per step

Exits 0 on success, non-zero on any unhandled exception.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .fixtures.sample_mission import sample_mission_state
from .graph import build_graph
from .state import CandidatePlace, GraphState


def _coerce_state(raw: Any) -> GraphState:
    """Best-effort conversion of LangGraph step output to a GraphState."""
    if isinstance(raw, GraphState):
        return raw
    if isinstance(raw, dict):
        return GraphState.model_validate(raw)
    # Some LangGraph versions return AddableValuesDict / similar mappings.
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
    """In --verbose mode, print whatever LangGraph yielded at this step."""
    try:
        as_dict = payload if isinstance(payload, dict) else dict(payload)
    except Exception:
        as_dict = {"_raw": repr(payload)}

    # LangGraph's stream-mode "updates" yields {node_name: state_diff}.
    # We render that as one section per node.
    for node_name, value in as_dict.items():
        try:
            body = json.dumps(value, indent=2, default=str, sort_keys=True)
        except Exception:
            body = repr(value)
        console.print(Panel(body, title=f"step {step_idx}: {node_name}", expand=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the C2-slice VibeBite recommend graph.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Dump the full state diff after every node executes.",
    )
    args = parser.parse_args(argv)

    console = Console()
    console.print("[bold]VibeBite C2 demo[/bold] — building graph and loading fixture mission...")

    graph = build_graph()
    # Schema is a TypedDict (see graph.py for the Python 3.9 reasoning),
    # so we pass a plain dict in. Pydantic models inside the dict (e.g.
    # MemberPref) are fine — LangGraph just stores them on the channel.
    initial_state_dict = sample_mission_state().model_dump()

    final_payload: Any
    if args.verbose:
        # `stream_mode="updates"` yields per-node diffs we can pretty-print,
        # while `stream_mode="values"` would give us the cumulative state.
        # We capture the last cumulative state via a second pass / final invoke.
        console.print("[dim]Streaming node updates (verbose mode)...[/dim]\n")
        for i, chunk in enumerate(graph.stream(initial_state_dict, stream_mode="updates"), start=1):
            _dump_step(console, i, chunk)
        # Re-run to grab the cumulative final state — graphs are pure for C2.
        final_payload = graph.invoke(initial_state_dict)
    else:
        final_payload = graph.invoke(initial_state_dict)

    final_state = _coerce_state(final_payload)

    # If coercion failed (older/newer LangGraph contract), fall back to dict access.
    if isinstance(final_state, GraphState):
        constraints = final_state.group_constraints
        candidates = final_state.candidates
    else:
        constraints = final_payload.get("group_constraints") if isinstance(final_payload, dict) else None
        raw_cands = final_payload.get("candidates", []) if isinstance(final_payload, dict) else []
        candidates = [
            c if isinstance(c, CandidatePlace) else CandidatePlace.model_validate(c)
            for c in raw_cands
        ]

    console.print()
    _pretty_print_constraints(console, constraints)
    console.print()
    _pretty_print_top5(console, candidates)
    console.print("\n[bold green]Done.[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
