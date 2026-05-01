# vibebite-agents

LangGraph agent workflows for VibeBite. At checkpoint C1-C this package is
a skeleton: the `GraphState` schema (spec sec 8.1), prompt placeholders
(spec sec 9.3), an LLM client wrapper, a Google Places client wrapper, and
fixture-driven stubs for both external services. Real LangGraph nodes,
graph wiring, and the demo runner land in C2; the real OpenAI/Places
implementations land in C2/C3.

## Layout

```
vibebite_agents/
  state.py              GraphState / MemberPref / CandidatePlace
  prompts.py            Three prompt-template constants
  models.py             get_llm() returns StubLLM or OpenAILLM
  clients/
    places_client.py    GooglePlacesClient.text_search(...)
    places_stub.py      12 hand-crafted Atlanta restaurants
    llm_stub.py         stub_chat_completion(messages, response_model)
  fixtures/
    sample_mission.py   sample_mission_state() -> GraphState
```

## Stubs

The stubs ship populated fixture data so downstream nodes can be developed
without API keys. Selection is controlled by env vars, so flipping to real
clients later is just an env change.

| Env var                  | Effect                                                  |
| ------------------------ | ------------------------------------------------------- |
| `VIBEBITE_USE_STUBS=1`   | Force stubs for both LLM and Places. Highest priority.  |
| `OPENAI_API_KEY` unset   | LLM falls back to `StubLLM`.                            |
| `GOOGLE_PLACES_API_KEY` unset | Places falls back to fixture stub.                 |
| `OPENAI_MODEL`           | Real-client model id (defaults to `gpt-4o-mini`).       |

The fixture restaurants cover varied cuisines (italian, mexican, japanese,
thai, vegan, american, indian, korean, ethiopian, pizza, burgers, ramen),
price levels 1-4, ratings 3.5-4.8, and a mix of quiet/casual and lively
vibes — enough variety for the score node to produce non-trivial
rankings against the sample mission.

The LLM stub is a deterministic keyword spotter, not a model. It looks for
`vegetarian`, `vegan`, `cheap` / `budget`, `fancy`, `loud`, `quiet`,
`casual`, and `sushi` in the messages and produces a populated
`GroupConstraints` or `CandidateExplanation` Pydantic instance. Document
the exact mapping in `clients/llm_stub.py`.

## How the demo will work in C2

C2 will add `vibebite_agents/graph.py` plus the `nodes/` package and a
runner that wires it all together. The runner will:

1. Call `sample_mission_state()` to build the initial `GraphState`.
2. Invoke `recommend_v1` with that state and a (Sqlite or in-memory)
   LangGraph checkpointer.
3. Print the resulting `shortlist` with pros/cons.

With `VIBEBITE_USE_STUBS=1` the run uses no external services, so it is
safe to execute in CI and on a fresh checkout.

## Constraints

- Python 3.9 — every module starts with `from __future__ import annotations`.
- Pydantic v2.
- Runtime deps (declared in `pyproject.toml`): `pydantic`, `httpx`,
  `structlog`. LangGraph deliberately not added until C2.
