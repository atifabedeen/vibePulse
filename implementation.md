# VibeBite Master Build Spec

## 0. Project summary

Build **VibeBite**, a production-ready mobile app that helps groups find the best food spot based on vibe, budget, dietary restrictions, distance, group preferences, and real-time constraints.

The product should feel fun and social:

> "We want a cheap late-night spot, not too loud, good for 5 people, with vegetarian options, and the vibe should be casual but still cute."

The engineering should secretly demonstrate:

- AI agents
- autonomous workflows
- AI-powered decision systems
- monitoring and observability
- incident-style remediation
- Python automation
- SQL
- PostgreSQL
- LangGraph
- OpenAI API or Azure OpenAI
- MCP
- Prometheus
- Grafana
- OpenTelemetry
- production-grade backend design

This aligns with the target role because the role asks for AI agents, autonomous workflows, automation, reliability engineering, logs, metrics, incident analysis, and remediation systems.[^role]

---

## 1. Product name

### Name

VibeBite

### Tagline

Find the food spot your whole group can actually agree on.

### Product one-liner

VibeBite is a mobile AI agent app that collects group food preferences, searches nearby restaurants, ranks them by vibe and constraints, explains tradeoffs, runs a group vote, and replans when the group changes its mind.

---

## 2. Core user story

A user opens the app and creates a food mission.

Example:

> Dinner tonight in Atlanta. 5 people. Under $25 each. Not too loud. One vegetarian. One person refuses sushi. We want somewhere casual but still a good vibe.

The user invites friends.

Each friend submits preferences:

- budget
- distance tolerance
- cuisine likes
- cuisine dislikes
- dietary restrictions
- vibe preference
- noise tolerance
- seating preference
- urgency
- "I am starving" level

The AI agent system:

1. Parses messy natural language into structured constraints.
2. Searches restaurants using Google Places.
3. Normalizes candidates.
4. Scores restaurants against group preferences.
5. Explains why each restaurant fits or does not fit.
6. Creates a shortlist.
7. Runs a group vote.
8. Picks the best option and a backup.
9. Replans if a constraint changes.
10. Tracks failures, latency, API degradation, and agent decisions.

Google Places API returns location data and imagery for establishments.[^places-overview] Text Search returns places from a query like "pizza in New York" and accepts a location bias.[^places-textsearch] Place Details returns address, phone, rating, and reviews for a known place ID.[^places-details]

---

## 3. What the finished product must do

### MVP requirements

The app must support:

1. Account creation and login.
2. Create a food mission.
3. Invite friends to a mission through a shareable link.
4. Friends can join without complex onboarding.
5. Friends submit structured preferences and optional natural language comments.
6. AI parses all preferences into a shared group constraint profile.
7. App searches nearby places.
8. App ranks top candidates.
9. App shows top 5 restaurants with explanation cards.
10. App supports group voting.
11. App chooses a winner and one backup.
12. App supports replanning when a friend changes constraints.
13. App stores all agent runs, tool calls, scores, and decisions.
14. App has observability dashboards.
15. App has automated tests.
16. App can run locally using Docker Compose.
17. App can be deployed to a cloud environment.

### Production-grade requirements

The app must include:

1. OpenTelemetry tracing.
2. Prometheus metrics.
3. Grafana dashboards.
4. Structured logs.
5. Retry logic for external APIs.
6. Caching for Google Places results.
7. Agent audit logs.
8. Human approval for high-impact actions.
9. MCP tool server.
10. LangGraph workflows with persisted state.
11. Error handling for invalid agent output.
12. Rate-limit protection.
13. CI/CD with GitHub Actions.
14. Runbooks for common failures.
15. Load tests.
16. E2E mobile tests.
17. Backend unit and integration tests.

OpenTelemetry is a vendor-neutral framework for generating and exporting traces, metrics, and logs.[^otel] Prometheus alerting rules send alerts to Alertmanager, which handles grouping, silencing, inhibition, and notifications.[^prom-alerting]

---

## 4. Tech stack

### Mobile app

- React Native
- Expo
- TypeScript
- Expo Router
- NativeWind or Tamagui
- Zustand for client state
- TanStack Query for API state
- React Hook Form
- Zod
- Expo Location
- Expo Notifications
- Google Maps SDK or React Native Maps
- EAS Build

Expo is a production-grade React Native framework, and EAS Build produces App Store and Play Store binaries.[^expo][^eas]

### Backend

- Python 3.9
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0
- Alembic
- PostgreSQL 16
- pgvector
- Redis 7
- Celery or Dramatiq
- LangGraph
- OpenAI API or Azure OpenAI
- MCP server
- OpenTelemetry
- Prometheus client
- structlog
- pytest

FastAPI is a modern Python web framework using standard type hints.[^fastapi] pgvector enables vector similarity search inside Postgres.[^pgvector]

### Agent framework

- LangGraph for core multi-step workflows
- OpenAI API for LLM calls
- Pydantic schemas for structured outputs
- MCP for exposing tools, resources, and prompts

LangGraph's persistence layer supports durable execution: workflow state is saved so processes resume without repeating completed steps.[^langgraph-persistence] LangChain's human-in-the-loop middleware can pause execution when a tool call requires review.[^langchain-hitl] MCP servers expose resources, prompts, and tools to AI clients.[^mcp]

### Infrastructure

- Docker
- Docker Compose
- GitHub Actions
- AWS ECS Fargate or Render for backend
- AWS RDS PostgreSQL or Supabase Postgres
- Upstash Redis or AWS ElastiCache
- Grafana Cloud or self-hosted Grafana
- Prometheus
- OpenTelemetry Collector
- Optional OpenSearch for logs

### External APIs

- Google Places API
- Google Maps SDK
- OpenAI API or Azure OpenAI
- Optional Expo Push Notifications

---

## 5. Repository structure

Monorepo at `vibebite/` (local working dir is `vibePulse/` for historical reasons; the canonical name is VibeBite).

```text
vibebite/
  README.md
  .gitignore
  .env.example
  .editorconfig
  docker-compose.yml
  Makefile
  pyproject.toml              # shared ruff/black/mypy config
  requirements-dev.txt        # shared dev tooling

  apps/
    mobile/                   # Expo React Native app
      app/                    # Expo Router routes
      src/
        components/
        screens/
        hooks/
        api/                  # generated from OpenAPI
        state/                # Zustand stores
        types/
        utils/
        theme/
      assets/
      package.json
      app.json
      eas.json
      tsconfig.json

    admin/                    # Next.js dashboard for ops/observability
      src/
        app/
        components/
        lib/
        dashboards/
      package.json
      tsconfig.json

  services/
    api/                      # FastAPI public API
      app/
        main.py
        config.py
        database.py
        dependencies.py
        logging.py
        telemetry.py

        api/v1/
          auth.py
          users.py
          missions.py
          preferences.py
          places.py
          rankings.py
          votes.py
          agents.py
          health.py

        models/               # SQLAlchemy ORM
          user.py mission.py preference.py place.py
          ranking.py vote.py agent_run.py incident.py

        schemas/              # Pydantic request/response
          auth.py user.py mission.py preference.py
          place.py ranking.py vote.py agent.py

        services/             # business logic, reused by MCP server
          auth_service.py
          mission_service.py
          places_service.py
          ranking_service.py
          notification_service.py
          cache_service.py

        repositories/         # SQLAlchemy data access
          user_repo.py mission_repo.py places_repo.py
          ranking_repo.py agent_repo.py

        tests/
          unit/
          integration/

      alembic/
      pyproject.toml
      Dockerfile

    agents/                   # LangGraph workflows
      vibebite_agents/
        graph.py              # graph builder
        state.py              # Pydantic state schema
        prompts.py
        models.py             # LLM client wrappers
        tools.py              # internal tool wrappers
        nodes/
          parse_preferences.py
          search_places.py
          normalize_places.py
          score_candidates.py
          explain_candidates.py
          create_poll.py
          collect_votes.py
          select_winner.py
          replan.py
          reliability_check.py
        evals/
          test_preference_parsing.py
          test_ranking.py
          test_replanning.py
      pyproject.toml
      Dockerfile

    mcp_server/               # Model Context Protocol server
      server.py
      tools/
        search_places.py
        get_place_details.py
        rank_candidates.py
        create_poll.py
        send_notification.py
        inspect_failed_jobs.py
        replan_mission.py
      resources/
        mission_resource.py
        place_resource.py
        agent_run_resource.py
      prompts/
        group_food_recommendation.py
        restaurant_tradeoff_explanation.py
        incident_summary.py
      pyproject.toml
      Dockerfile

    worker/                   # Background job runner (Celery/Dramatiq)
      app.py
      jobs/
        refresh_places_cache.py
        retry_failed_agent_runs.py
        send_push_notifications.py
        compute_metrics.py
      pyproject.toml
      Dockerfile

  infra/
    prometheus/
      prometheus.yml
      alert_rules.yml
    grafana/
      dashboards/
        api-dashboard.json
        agent-dashboard.json
        places-dashboard.json
        mobile-dashboard.json
    otel/
      collector-config.yml
    k8s/
      api-deployment.yml agents-deployment.yml
      worker-deployment.yml postgres.yml redis.yml
    terraform/
      main.tf variables.tf outputs.tf

  docs/
    architecture.md api.md database.md agents.md
    mcp.md observability.md deployment.md testing.md
    runbooks/
      places-api-degraded.md
      agent-output-invalid.md
      ranking-confidence-low.md
      push-notification-failed.md
      database-latency-high.md
    incidents/
      sample-incident-places-api-degraded.md

  tests/
    load/
      k6-missions.js
      k6-ranking.js
    e2e/
      mobile-flow.md
```

### 5.1 File-by-file responsibilities

**`apps/mobile/`** — Expo + React Native client. Owns: UI, client-side validation (Zod), API client (TanStack Query against the FastAPI OpenAPI spec), client state (Zustand), real-time poll updates (polling for v1, WebSocket optional later). Depends on: `services/api` OpenAPI schema (codegen at build time).

**`apps/admin/`** — Next.js operator console. Read-only dashboards for agent runs, incidents, Places cache hit rate. Depends on: `services/api` admin endpoints and Grafana embed URLs.

**`services/api/`** — FastAPI application. Owns: HTTP boundary, authentication (JWT), authorization, request validation, persistence (SQLAlchemy + Alembic), and `services/` (business logic that is **reused by `mcp_server` via direct import** — see §9). Exposes `/api/v1/*` and `/health`. Emits OTel spans, Prom metrics, and structlog JSON.

**`services/agents/`** — LangGraph workflows. Owns: the graph definition, state schema, node implementations, evals. Calls `services/api` business logic via shared package import (in-process where possible) or HTTP for cross-service calls. Persists graph state via LangGraph's Postgres checkpointer (separate schema from app DB; see §6).

**`services/mcp_server/`** — MCP server exposing tools/resources/prompts to external AI clients (Claude Desktop, Cursor, etc.). Imports `services/api/app/services/` directly to avoid logic duplication.

**`services/worker/`** — Celery/Dramatiq worker for: Places cache refresh, retry of failed agent runs, push notification dispatch, metric rollups. Triggered by Redis broker; reads/writes the same Postgres as `services/api`.

**`infra/prometheus/`** — Prometheus scrape config and alert rules consumed by Alertmanager.
**`infra/grafana/`** — Dashboard JSON, version-controlled and provisioned via Grafana's file provisioner.
**`infra/otel/`** — OTel Collector pipeline config (receivers → processors → exporters).
**`infra/k8s/` / `infra/terraform/`** — production deploy manifests (M7).

---

## 6. Data model

PostgreSQL 16 with the `pgvector` and `pgcrypto` extensions enabled. Alembic owns the **public** schema below. **LangGraph owns its own `langgraph` schema**, created by its checkpointer migrations — Alembic does not manage it. Two parallel migration tools is intentional and avoids accidental coupling.

All timestamps are `timestamptz`. All primary keys are `uuid` defaulting to `gen_random_uuid()` from `pgcrypto`. Soft-delete is intentionally **not** used; deletion is hard-delete with audit rows in `agent_runs`/`incidents` where relevant.

### 6.1 DDL

```sql
-- Extensions
create extension if not exists pgcrypto;
create extension if not exists vector;

-- users: account holders
create table users (
  id              uuid primary key default gen_random_uuid(),
  email           citext unique not null,
  password_hash   text not null,
  display_name    text not null,
  avatar_url      text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  deleted_at      timestamptz  -- only set during GDPR-style erasure
);
create index users_email_idx on users (email);

-- missions: a single group decision
create table missions (
  id              uuid primary key default gen_random_uuid(),
  creator_id      uuid not null references users(id) on delete restrict,
  title           text not null,
  description     text,
  status          text not null check (status in
                  ('draft','collecting','ranking','voting','decided','cancelled')),
  location_lat    double precision not null,
  location_lng    double precision not null,
  search_radius_m integer not null default 3000,
  scheduled_for   timestamptz,
  winner_place_id uuid references places(id),
  backup_place_id uuid references places(id),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);
create index missions_creator_idx on missions (creator_id);
create index missions_status_idx on missions (status);

-- mission_members: who is in the mission
create table mission_members (
  mission_id      uuid not null references missions(id) on delete cascade,
  user_id         uuid not null references users(id) on delete cascade,
  role            text not null check (role in ('owner','member')),
  joined_at       timestamptz not null default now(),
  primary key (mission_id, user_id)
);

-- mission_invites: shareable-link invites (MVP req #3)
-- Each invite has a token; redeeming creates a mission_members row.
create table mission_invites (
  id              uuid primary key default gen_random_uuid(),
  mission_id      uuid not null references missions(id) on delete cascade,
  token           text unique not null,                -- random url-safe
  expires_at      timestamptz not null,
  max_uses        integer not null default 10,
  uses            integer not null default 0,
  created_at      timestamptz not null default now()
);
create index mission_invites_mission_idx on mission_invites (mission_id);

-- preferences: one row per (mission, user); edited as constraints change
create table preferences (
  mission_id              uuid not null references missions(id) on delete cascade,
  user_id                 uuid not null references users(id) on delete cascade,
  budget_max_cents        integer,
  distance_tolerance_m    integer,
  cuisines_like           text[] not null default '{}',
  cuisines_dislike        text[] not null default '{}',
  dietary_restrictions    text[] not null default '{}',
  vibe                    text,                           -- free text
  noise_tolerance         smallint check (noise_tolerance between 0 and 5),
  seating_preference      text,                           -- 'indoor','outdoor','either'
  urgency                 smallint check (urgency between 0 and 5),
  hunger_level            smallint check (hunger_level between 0 and 5),
  raw_comment             text,                           -- natural-language input
  parsed_at               timestamptz,                    -- when AI parsed raw_comment
  updated_at              timestamptz not null default now(),
  primary key (mission_id, user_id)
);

-- places: cached Google Places + embeddings for vibe similarity
create table places (
  id              uuid primary key default gen_random_uuid(),
  google_place_id text unique not null,
  name            text not null,
  address         text,
  lat             double precision not null,
  lng             double precision not null,
  price_level     smallint check (price_level between 0 and 4),
  rating          numeric(2,1),
  user_rating_ct  integer,
  cuisines        text[] not null default '{}',
  raw_blob        jsonb not null,                         -- full Places payload
  vibe_embedding  vector(1536),                           -- OpenAI text-embedding-3-small
  fetched_at      timestamptz not null default now(),
  expires_at      timestamptz not null,                   -- TTL: 7 days
  created_at      timestamptz not null default now()
);
create index places_google_id_idx on places (google_place_id);
create index places_expires_idx   on places (expires_at);
create index places_vibe_ivfflat_idx on places using ivfflat (vibe_embedding vector_cosine_ops);

-- rankings: one row per (mission, place) per ranking run
create table rankings (
  id              uuid primary key default gen_random_uuid(),
  mission_id      uuid not null references missions(id) on delete cascade,
  place_id        uuid not null references places(id),
  agent_run_id    uuid not null references agent_runs(id),
  rank            integer not null,
  score           numeric(5,2) not null,                  -- 0.00 - 100.00
  reasons         jsonb not null,                         -- {pros:[],cons:[]}
  created_at      timestamptz not null default now()
);
create index rankings_mission_run_idx on rankings (mission_id, agent_run_id);

-- votes: one row per (mission, user, place) — supports approval voting
create table votes (
  mission_id      uuid not null references missions(id) on delete cascade,
  user_id         uuid not null references users(id) on delete cascade,
  place_id        uuid not null references places(id),
  weight          smallint not null default 1,            -- 1=upvote, -1=veto
  created_at      timestamptz not null default now(),
  primary key (mission_id, user_id, place_id)
);

-- agent_runs: top-level LangGraph executions
create table agent_runs (
  id              uuid primary key default gen_random_uuid(),
  mission_id      uuid not null references missions(id) on delete cascade,
  graph_name      text not null,                          -- 'recommend_v1','replan_v1'
  status          text not null check (status in
                  ('running','succeeded','failed','interrupted','cancelled')),
  trigger         text not null,                          -- 'user','cron','webhook'
  input           jsonb not null,
  output          jsonb,
  error           text,
  started_at      timestamptz not null default now(),
  finished_at     timestamptz,
  total_tokens    integer,
  total_cost_usd  numeric(10,6)
);
create index agent_runs_mission_idx on agent_runs (mission_id, started_at desc);
create index agent_runs_status_idx  on agent_runs (status);

-- agent_run_steps: one row per LangGraph node execution
create table agent_run_steps (
  id              uuid primary key default gen_random_uuid(),
  agent_run_id    uuid not null references agent_runs(id) on delete cascade,
  node_name       text not null,
  status          text not null,
  input           jsonb,
  output          jsonb,
  tool_calls      jsonb,                                  -- list of {name,args,result}
  error           text,
  latency_ms      integer,
  started_at      timestamptz not null,
  finished_at     timestamptz
);
create index agent_run_steps_run_idx on agent_run_steps (agent_run_id, started_at);

-- incidents: detected reliability issues (Places degraded, agent loops, etc.)
create table incidents (
  id              uuid primary key default gen_random_uuid(),
  kind            text not null,                          -- e.g. 'places_api_degraded'
  severity        text not null check (severity in ('info','warn','error','critical')),
  status          text not null check (status in ('open','acknowledged','resolved')),
  title           text not null,
  details         jsonb not null,
  related_run_id  uuid references agent_runs(id),
  opened_at       timestamptz not null default now(),
  resolved_at     timestamptz
);
create index incidents_status_idx on incidents (status, opened_at desc);
```

### 6.2 Retention

| Table | Retention | Trigger |
|---|---|---|
| `users` | indefinite, until erasure request | DSR endpoint sets `deleted_at` and scrubs PII |
| `missions` | 90 days after `decided`/`cancelled` | nightly worker job |
| `preferences` | tied to mission | cascade |
| `places` | TTL `expires_at` (7 days) | worker `refresh_places_cache.py` |
| `agent_runs` / `agent_run_steps` | 30 days | nightly worker job |
| `incidents` | 365 days | manual archive |

### 6.3 LangGraph checkpointer

LangGraph's Postgres checkpointer manages a separate `langgraph` schema with its own tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`). This is created by `langgraph.checkpoint.postgres.PostgresSaver.setup()` on first run, **not** by Alembic. The `agent_runs` table above is our app-level audit log; the `langgraph` schema is the workflow engine's state. They are intentionally separate.

---

## 7. REST API

Base URL: `/api/v1`. JSON only. Auth: Bearer JWT in `Authorization` header unless noted. All errors follow RFC 7807 problem+json: `{type, title, status, detail, instance}`. Standard error codes: `400` validation, `401` unauthenticated, `403` unauthorized, `404` not found, `409` conflict, `429` rate limited, `500` server error, `503` upstream degraded.

### 7.1 `auth.py` — `/api/v1/auth`

| Method | Path | Auth | Request | Response | Errors |
|---|---|---|---|---|---|
| POST | `/register` | none | `{email, password, display_name}` | `201 {user, access_token, refresh_token}` | 400, 409 |
| POST | `/login` | none | `{email, password}` | `200 {user, access_token, refresh_token}` | 400, 401 |
| POST | `/refresh` | refresh token | `{refresh_token}` | `200 {access_token}` | 401 |
| POST | `/logout` | yes | — | `204` | — |
| GET  | `/me` | yes | — | `200 User` | 401 |

### 7.2 `users.py` — `/api/v1/users`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| PATCH | `/me` | yes | `{display_name?, avatar_url?}` | `200 User` |
| DELETE | `/me` | yes | — | `204` (DSR — scrubs PII, soft-deletes) |

### 7.3 `missions.py` — `/api/v1/missions`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/` | yes | `MissionCreate` | `201 Mission` |
| GET | `/` | yes | `?status=&limit=&cursor=` | `200 {items: Mission[], next_cursor}` |
| GET | `/{id}` | yes (member) | — | `200 MissionDetail` |
| PATCH | `/{id}` | yes (owner) | `MissionUpdate` | `200 Mission` |
| DELETE | `/{id}` | yes (owner) | — | `204` |
| POST | `/{id}/invites` | yes (owner) | `{expires_in_hours, max_uses}` | `201 Invite` |
| POST | `/invites/redeem` | yes | `{token}` | `200 Mission` |
| POST | `/{id}/replan` | yes (member) | `{reason}` | `202 {agent_run_id}` |

`MissionCreate`:
```json
{ "title": "string", "description": "string?",
  "location": {"lat": 0, "lng": 0}, "search_radius_m": 3000,
  "scheduled_for": "ISO-8601?" }
```

### 7.4 `preferences.py` — `/api/v1/missions/{mission_id}/preferences`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| PUT | `/me` | yes (member) | `PreferencePayload` | `200 Preference` |
| GET | `/` | yes (member) | — | `200 Preference[]` |
| POST | `/me/parse` | yes (member) | `{raw_comment}` | `200 Preference` (AI-parsed) |

`PreferencePayload` mirrors the `preferences` table columns.

### 7.5 `places.py` — `/api/v1/missions/{mission_id}/places`

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/` | yes (member) | `200 Place[]` (cached candidates for this mission) |
| GET | `/{place_id}` | yes (member) | `200 PlaceDetail` |
| POST | `/refresh` | yes (owner) | `202 {agent_run_id}` (force re-search) |

### 7.6 `rankings.py` — `/api/v1/missions/{mission_id}/rankings`

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/latest` | yes (member) | `200 {agent_run_id, items: Ranking[]}` |
| GET | `/runs/{agent_run_id}` | yes (member) | `200 {items: Ranking[]}` |

### 7.7 `votes.py` — `/api/v1/missions/{mission_id}/votes`

| Method | Path | Auth | Request | Response |
|---|---|---|---|---|
| PUT | `/me` | yes (member) | `{place_id, weight}` (weight ∈ {-1, 1}) | `200 Vote[]` |
| GET | `/` | yes (member) | — | `200 {tally: {place_id: {up, veto}}}` |
| POST | `/finalize` | yes (owner) | — | `200 {winner: Place, backup: Place}` |

### 7.8 `agents.py` — `/api/v1/missions/{mission_id}/agents`

| Method | Path | Auth | Response |
|---|---|---|---|
| GET | `/runs` | yes (member) | `200 AgentRun[]` |
| GET | `/runs/{run_id}` | yes (member) | `200 AgentRunDetail` (includes steps) |
| POST | `/runs/{run_id}/approve` | yes (owner) | `200` (resumes interrupted graph; see §8) |
| POST | `/runs/{run_id}/reject` | yes (owner) | `200` |

### 7.9 `health.py` — `/health`, `/ready`, `/metrics`

- `GET /health` → `200 {status:"ok"}` always (liveness).
- `GET /ready` → `200` if DB+Redis reachable, else `503`.
- `GET /metrics` → Prometheus exposition format. No auth (cluster-internal only).

### 7.10 Inbound callbacks

There are **no third-party webhooks** in v1. Google Places does not push. Expo Push delivery receipts are **polled** by `services/worker/jobs/send_push_notifications.py`, not pushed. If we add Stripe or similar later, callbacks will live under `/api/v1/webhooks/{provider}` with signature verification middleware — pinning the URL shape now so future additions don't reshape v1.

---

## 8. LangGraph workflow

The agent system is a single graph, `recommend_v1`, defined in `services/agents/vibebite_agents/graph.py`. A second graph `replan_v1` reuses most nodes but starts at `parse_preferences` with the new constraints injected.

### 8.1 State schema (`state.py`)

`from __future__ import annotations` defers evaluation of annotations, which lets us
keep the modern `X | None` union syntax even on Python 3.9. Every backend module
that uses these annotations should include the same import at the top.

```python
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal
from uuid import UUID

class MemberPref(BaseModel):
    user_id: UUID
    structured: dict          # snapshot of preferences row
    raw_comment: str | None

class CandidatePlace(BaseModel):
    place_id: UUID
    google_place_id: str
    name: str
    score: float | None = None
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)

class GraphState(BaseModel):
    # inputs
    mission_id: UUID
    member_prefs: list[MemberPref]
    location: tuple[float, float]
    search_radius_m: int

    # derived
    group_constraints: dict | None = None     # parse_preferences output
    candidates: list[CandidatePlace] = Field(default_factory=list)
    shortlist: list[CandidatePlace] = Field(default_factory=list)

    # voting
    poll_id: UUID | None = None
    votes: dict[str, dict] = Field(default_factory=dict)

    # decision
    winner: CandidatePlace | None = None
    backup: CandidatePlace | None = None

    # control
    needs_human_approval: bool = False
    approval_decision: Literal["approve", "reject"] | None = None

    # observability
    agent_run_id: UUID
```

### 8.2 Nodes

| Node | Input (state fields read) | Output (state fields written) | Side effects |
|---|---|---|---|
| `parse_preferences` | `member_prefs` | `group_constraints` | OpenAI call w/ structured output (Pydantic); writes parsed result to `preferences.parsed_at` |
| `search_places` | `group_constraints`, `location`, `search_radius_m` | `candidates` (raw) | Google Places Text Search; upserts into `places` table; emits `places_api_calls_total` |
| `normalize_places` | `candidates` | `candidates` (filtered) | Drops candidates with insufficient data; tags missing fields |
| `score_candidates` | `candidates`, `group_constraints` | `candidates` (with score) | Deterministic scoring fn (no LLM); writes `rankings` rows |
| `explain_candidates` | `candidates` (top 5) | `shortlist` (with pros/cons) | OpenAI call per candidate; writes `rankings.reasons` |
| `create_poll` | `shortlist` | `poll_id` | Creates a poll row (votes scoped to mission) |
| `collect_votes` | `poll_id` | `votes` | **Polls votes** until quorum or timeout (LangGraph interrupt / `wait_for_event`) |
| `select_winner` | `votes`, `shortlist` | `winner`, `backup`, `needs_human_approval=true` | **HITL interrupt** — graph pauses; resumed by `POST /agents/runs/{id}/approve` |
| `replan` | new constraint trigger | `group_constraints` (updated) | Branches back to `search_places` if location changed, else `score_candidates` |
| `reliability_check` | `state` (always-on tap) | — | Detects API degradation, low-confidence rankings; writes `incidents` |

### 8.3 Edges

```text
START → parse_preferences → search_places → normalize_places →
  score_candidates → explain_candidates → create_poll →
  collect_votes → select_winner → [HITL interrupt] →
  (if approved) END
  (if rejected) → replan → score_candidates → ...

reliability_check is a parallel node attached after every external-API node
(search_places, explain_candidates) and writes incidents without blocking the path.
```

### 8.4 Checkpointer & HITL

- Checkpointer: `langgraph.checkpoint.postgres.PostgresSaver`, schema `langgraph` (see §6.3).
- Interrupt points (explicit): **`select_winner`** (group/owner must confirm winner) and **`replan`** (owner must confirm constraint change is intentional, not a misclick). All other nodes run autonomously.
- Resumption: API endpoint `POST /agents/runs/{id}/approve|reject` calls `graph.update_state(...)` then `graph.invoke(None, config)` to continue.
- Timeouts: `collect_votes` has a 30-minute soft timeout; if quorum not reached, proceeds with partial votes and writes an `incidents` row (`severity=warn`).

### 8.5 Error handling

- Any node raising → `agent_runs.status='failed'`, `error` populated, `incidents` row written.
- Invalid LLM output (Pydantic validation fail) → one retry with stricter prompt; second failure → `failed`.
- External API 429/5xx → exponential backoff (1s, 4s, 16s) up to 3 attempts; persistent failure → `incidents` row, `severity=error`.

---

## 9. MCP server

`services/mcp_server/server.py` runs the official Python MCP SDK in stdio mode (local) and SSE/HTTP mode (deployed). It exposes **tools**, **resources**, and **prompts**.

**Architecture decision:** MCP tool implementations **import `services/api/app/services/` directly** — they do not call the FastAPI HTTP API. This avoids logic duplication between `mcp_server/tools/search_places.py` and `services/api/app/services/places_service.py`. Both services are deployed as separate containers but share the `services/api/app/services/` Python package via a workspace dependency.

### 9.1 Tools

Each tool has: name, JSON input schema, JSON output schema, side effects.

| Name | Input | Output | Side effects |
|---|---|---|---|
| `search_places` | `{query, lat, lng, radius_m, max_results?}` | `{places: Place[]}` | Hits Google Places (cached); upserts `places` |
| `get_place_details` | `{google_place_id}` | `Place` | Hits Place Details (cached) |
| `rank_candidates` | `{mission_id, place_ids[], constraints}` | `{rankings: Ranking[]}` | Writes `rankings` rows |
| `create_poll` | `{mission_id, place_ids[]}` | `{poll_id}` | Creates poll |
| `send_notification` | `{user_ids[], title, body, data?}` | `{message_ids[]}` | Calls Expo Push; queues delivery-receipt poll |
| `inspect_failed_jobs` | `{since?, limit?}` | `{runs: AgentRunSummary[]}` | none (read-only) |
| `replan_mission` | `{mission_id, reason}` | `{agent_run_id}` | Triggers `replan_v1` graph |

### 9.2 Resources

| URI pattern | Returns |
|---|---|
| `vibebite://missions/{id}` | Full mission JSON (mission + members + latest ranking + winner) |
| `vibebite://places/{id}` | Place JSON + cached Google blob |
| `vibebite://agent-runs/{id}` | Agent run + all steps |

### 9.3 Prompts

| Name | Purpose | Variables |
|---|---|---|
| `group_food_recommendation` | Used by `parse_preferences` and `explain_candidates` | `member_prefs`, `location` |
| `restaurant_tradeoff_explanation` | Used by `explain_candidates` per place | `place`, `group_constraints` |
| `incident_summary` | Used by `reliability_check` to write incident `details` | `signals`, `recent_runs` |

---

## 10. Observability

OpenTelemetry is the single source of truth: every service is instrumented to emit traces, metrics, and logs to an **OTel Collector**, which fans out to Prometheus (metrics), a logs backend (Loki / OpenSearch), and a traces backend (Tempo / Jaeger). Grafana reads all three.

### 10.1 Span naming

Convention: `<service>.<component>.<operation>`. Examples:

- `api.http.POST /api/v1/missions` (auto from FastAPI instrumentor)
- `api.db.query users.select_by_email`
- `agents.graph.recommend_v1`
- `agents.node.parse_preferences`
- `agents.tool.openai.chat_completion`
- `mcp.tool.search_places`
- `worker.job.refresh_places_cache`

Mandatory span attributes on every span: `service.name`, `service.version`, `deployment.environment`, `mission_id` (when present), `agent_run_id` (when present), `user_id` (when authenticated, hashed).

### 10.2 Metrics

Prometheus client metrics, all with `service` and `env` labels:

| Metric | Type | Labels (extra) | Purpose |
|---|---|---|---|
| `http_requests_total` | counter | `method, path, status` | API request volume |
| `http_request_duration_seconds` | histogram | `method, path` | API latency |
| `db_query_duration_seconds` | histogram | `op, table` | DB latency |
| `places_api_calls_total` | counter | `endpoint, status` | Google Places usage |
| `places_cache_hit_ratio` | gauge | — | Computed by worker job |
| `agent_runs_total` | counter | `graph, status` | LangGraph completions |
| `agent_run_duration_seconds` | histogram | `graph` | End-to-end graph latency |
| `agent_node_duration_seconds` | histogram | `graph, node` | Per-node latency |
| `llm_tokens_total` | counter | `model, kind` (prompt/completion) | Cost tracking |
| `llm_cost_usd_total` | counter | `model` | Cost tracking |
| `incidents_open` | gauge | `kind, severity` | Operational health |
| `mcp_tool_calls_total` | counter | `tool, status` | MCP usage |

### 10.3 Logs

Structured JSON via `structlog`. Mandatory fields: `ts`, `level`, `service`, `env`, `trace_id`, `span_id`, `event`. Domain fields when applicable: `mission_id`, `user_id`, `agent_run_id`, `node_name`. Never log raw preferences or PII — log IDs and let dashboards join.

### 10.4 Dashboards

JSON committed under `infra/grafana/dashboards/`:

- `api-dashboard.json`: RPS, p50/p95/p99 latency by route, error rate, top slow routes.
- `agent-dashboard.json`: runs/min by status, p95 graph duration, per-node latency heatmap, LLM token spend, top failure modes.
- `places-dashboard.json`: Google Places call rate, error rate, cache hit ratio, expiring cache count.
- `mobile-dashboard.json`: client-reported errors and screen latency (Sentry-or-equivalent webhook into the API).

### 10.5 Alert rules

Defined in `infra/prometheus/alert_rules.yml`. Each alert links to a runbook in `docs/runbooks/`.

| Alert | Expr (sketch) | Severity | Runbook |
|---|---|---|---|
| `PlacesAPIDegraded` | `rate(places_api_calls_total{status=~"5.."}[5m]) > 0.05` | warn | `places-api-degraded.md` |
| `AgentOutputInvalid` | `rate(agent_runs_total{status="failed",reason="schema"}[10m]) > 0.1` | warn | `agent-output-invalid.md` |
| `RankingConfidenceLow` | sustained low `score` p95 < 40 | info | `ranking-confidence-low.md` |
| `PushNotificationFailed` | `rate(... push_failures_total[10m]) > 0.2` | warn | `push-notification-failed.md` |
| `DatabaseLatencyHigh` | `histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m])) > 0.5` | error | `database-latency-high.md` |
| `APIErrorRateHigh` | `rate(http_requests_total{status=~"5.."}[5m]) > 0.02` | error | (generic) |

### 10.6 Trace context propagation

Five hops (mobile → api → agents → mcp → worker) means a single user action can produce a fragmented trace if any link drops context. Rules:

- **Mobile → API**: client generates a `traceparent` (W3C Trace Context) header on every outbound request and attaches it to every retry of the same logical action with the same trace ID.
- **API → DB**: SQLAlchemy instrumentor automatically nests `db.query` spans under the active HTTP span.
- **API → Agents**: when API enqueues a graph run (or invokes in-process), the current span's `traceparent` is serialized into the `agent_runs.input` JSON under `_trace.traceparent`. The graph entry node restores it.
- **Agents → MCP**: MCP stdio/SSE messages carry `traceparent` in a custom `_meta.traceparent` field; the MCP server SDK is wrapped to extract and use it.
- **API → Worker (Celery/Dramatiq)**: task headers carry `traceparent`. Worker entrypoint extracts it before the job runs.

If a hop drops the context, that's a bug; `reliability_check` logs an incident.

---

## 11. Security & secrets

### 11.1 Auth

JWT-based, two-token model:

- **Access token**: 15-minute expiry, signed with `JWT_SECRET` (HS256 in dev, RS256 in prod with a KMS-managed key). Carried in `Authorization: Bearer ...`.
- **Refresh token**: 30-day expiry, opaque random string; stored hashed in `users.refresh_token_hash` (added to schema in §6 v2). Rotated on every refresh.

Password hashing: `argon2id`. Email verification: out of scope for v1; mark accounts `email_verified=false` and gate sensitive endpoints behind verification when added.

### 11.2 Authorization

Mission-scoped: every endpoint under `/api/v1/missions/{id}/*` checks `mission_members` membership. Owner-only routes additionally check `role='owner'`. No cross-tenant access.

### 11.3 Rate limiting

Redis-backed token bucket via `slowapi`. Limits:

- Anonymous (login/register): 10 req/min per IP.
- Authenticated user: 120 req/min per user.
- Places search endpoints: 30 req/min per mission.
- Agent run triggers (`POST /missions/{id}/replan`): 5 per mission per hour.

Returns `429` with `Retry-After`. Limit hits emit a span event and increment `rate_limit_hits_total`.

### 11.4 Env var inventory

Every var listed here must appear in `.env.example`. Real values live only in deploy secret stores (AWS Secrets Manager / GitHub Actions secrets).

| Var | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | api, agents, worker | Postgres connection |
| `LANGGRAPH_DATABASE_URL` | agents | Defaults to `DATABASE_URL`; override if checkpointer goes elsewhere |
| `REDIS_URL` | api, worker | Cache + Celery broker |
| `JWT_SECRET` | api | Access-token signing key |
| `JWT_REFRESH_SECRET` | api | Refresh-token signing key |
| `OPENAI_API_KEY` | agents, mcp | LLM calls |
| `OPENAI_MODEL` | agents, mcp | Default model id |
| `GOOGLE_PLACES_API_KEY` | api, agents, mcp | Restaurant search |
| `EXPO_ACCESS_TOKEN` | worker | Push notifications |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | all | OTel Collector address |
| `OTEL_SERVICE_NAME` | each service sets its own | span attribute |
| `LOG_LEVEL` | all | structlog level |
| `ENV` | all | `dev` / `staging` / `prod` |
| `SENTRY_DSN` | mobile, api | Error reporting (optional) |
| `MCP_SERVER_PORT` | mcp | SSE/HTTP port (stdio mode if unset) |

### 11.5 PII & data retention

VibeBite stores: email, display name, location coordinates, group preferences (incl. dietary restrictions which are sensitive in some jurisdictions), and Google Places blobs.

- **Email/display name**: retained until account deletion. DSR endpoint (`DELETE /users/me`) sets `users.deleted_at`, scrubs `email`/`display_name`/`avatar_url`, and orphans foreign keys via `on delete restrict` so analytics tables stay valid but can't re-identify.
- **Location**: only stored on `missions.location_lat/lng`; not retained on user accounts.
- **Preferences**: cascade-deleted with mission (90 days post-decision).
- **Places blobs**: 7-day TTL; Google ToS allows caching but not indefinite storage.
- **Agent runs**: 30-day TTL; logs may include parsed preferences in `input`/`output` JSON, so retention here is the binding constraint.
- **Logs**: 30-day TTL in the logs backend.

DSR turnaround target: 30 days. Background job `gdpr_purge.py` (added in M7) iterates `users.deleted_at IS NOT NULL`.

### 11.6 Secrets handling in CI

GitHub Actions secrets only. `.env` is in `.gitignore`. Pre-commit hook (`detect-secrets` or `gitleaks`) added in M0.5 to block commits containing high-entropy strings.

---

## 12. Testing strategy

| Layer | Tool | Scope | Target |
|---|---|---|---|
| Unit (Python) | pytest | pure functions in `services/api/app/services/`, scoring logic, parsing | 80% line coverage on `services/` and `repositories/` |
| Integration (Python) | pytest + testcontainers (Postgres, Redis) | API routes end-to-end against real DB | All `/api/v1/*` happy paths + 1 failure path each |
| Agent evals | pytest + recorded LLM responses (vcr-style) | Each LangGraph node in isolation, plus end-to-end graph on fixture missions | Listed under `services/agents/vibebite_agents/evals/` |
| Contract | OpenAPI schema diff in CI | Prevents breaking the mobile client | Hard fail on incompatible change |
| Mobile unit | Jest + React Testing Library | Components, hooks, Zod schemas | 60% line coverage |
| Mobile E2E | Maestro | Critical flows: create mission, invite, vote, see winner | All 4 flows green per build |
| Load | k6 | `tests/load/k6-missions.js`, `k6-ranking.js` | API p95 < 300ms at 50 RPS sustained |
| Chaos / reliability | manual + scripted | Kill Places API, force LLM 429, sever Redis | Each maps to a runbook in `docs/runbooks/` |

CI pipeline (M0.5):

1. Lint (ruff, black --check, mypy, eslint, prettier --check).
2. Unit tests (Python + JS) in parallel.
3. Integration tests with services up via docker-compose.
4. Mobile bundle check (Expo prebuild).
5. OpenAPI schema check.
6. Build container images and push to GHCR on `main` only.

---

## 13. Milestone roadmap

Each milestone is one or more PRs, ends in a release tag, and has an explicit Definition of Done. Commits within a milestone push to `main`; milestone completion bumps the tag.

### M0 — Repo scaffold
- `.gitignore`, `.env.example`, `.editorconfig`, README, `requirements-dev.txt`, root `pyproject.toml` with shared tool config, Python venv.
- **DoD**: clone → `python3 -m venv .venv && pip install -r requirements-dev.txt` → `ruff check .` returns 0 issues on the (empty) tree.

### M0.5 — CI skeleton
- `.github/workflows/ci.yml`: lint + tests on PR; container build on `main`.
- pre-commit config; `gitleaks` secret scan.
- **DoD**: a no-op PR turns CI green.

### M1 — Auth + missions
- `services/api/` scaffold (FastAPI + SQLAlchemy + Alembic).
- Migrations for `users`, `missions`, `mission_members`, `mission_invites`.
- Endpoints: `auth.py` (full), `users.py` (full), `missions.py` (POST, GET, GET by id, invites, redeem).
- Integration tests for all endpoints.
- **DoD**: a curl flow can register, login, create mission, generate invite, redeem from a second account.

### M2 — Places integration
- Migrations for `places`, `preferences`.
- Endpoints: `preferences.py`, `places.py`.
- `places_service.py` with Google Places client, Redis cache, retry/backoff.
- Worker job `refresh_places_cache.py`.
- **DoD**: hitting `GET /missions/{id}/places` returns cached results on second call within 5 minutes; cache hit metric flips.

### M3 — LangGraph parser + ranker
- `services/agents/` scaffold.
- Migrations for `rankings`, `agent_runs`, `agent_run_steps`.
- Nodes: `parse_preferences`, `search_places`, `normalize_places`, `score_candidates`, `explain_candidates`, `reliability_check`.
- Graph runs end-to-end (no voting yet); HITL deferred to M4.
- Eval suite for `parse_preferences` and `score_candidates`.
- **DoD**: a fixture mission with 5 members produces a ranked top-5 with pros/cons per place.

### M4 — Voting + winner
- Migrations for `votes`.
- Nodes: `create_poll`, `collect_votes`, `select_winner`, `replan`.
- Endpoints: `votes.py`, `agents.py` (incl. approve/reject).
- HITL interrupt at `select_winner` and `replan`.
- **DoD**: a fixture mission completes through to a winner+backup; rejecting at the HITL gate triggers `replan` and produces a new shortlist.

### M5 — MCP server
- `services/mcp_server/` scaffold using the official Python MCP SDK.
- Tools, resources, prompts as defined in §9.
- Stdio mode for local; SSE/HTTP mode for deploy.
- **DoD**: `mcp-cli` (or Claude Desktop) can call `search_places`, `rank_candidates`, and read a mission resource.

### M6 — Observability
- OTel SDK wired into all services.
- Prometheus exposition on `/metrics`.
- Grafana dashboards committed and provisioned.
- Alert rules + runbooks.
- Sample incident doc.
- **DoD**: a synthetic load run shows traces spanning api → agents → mcp; one alert fires and resolves cleanly.

### M7 — Deploy
- Docker images for each service.
- Terraform for AWS (ECS Fargate, RDS, ElastiCache) **or** Render blueprint as the simpler path.
- GitHub Actions deploy job, gated on tag.
- DSR purge job.
- **DoD**: production URL serves `/health=ok`; a real mission flow runs end-to-end against the deployed stack.

### Mobile (parallel track)
- M-Mobile-1: Expo app skeleton, auth screens, mission list.
- M-Mobile-2: preferences form, mission detail, places list.
- M-Mobile-3: voting UI, winner reveal.
- M-Mobile-4: push notifications, deep links from invites.
- Each gated on the corresponding backend milestone.

---

## 14. Local development

### 14.1 Prerequisites

- Python 3.9 (matches the system Python on the dev machine; bump intentionally if needed)
- Node 20 LTS + npm/pnpm (only when working on `apps/mobile`)
- Docker Desktop (only from M2 onward)
- An OpenAI API key and a Google Cloud project with Places API enabled (free tier for development)

### 14.2 First-time setup

```bash
git clone git@github.com:atifabedeen/vibePulse.git
cd vibePulse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env       # then fill in real values locally
pre-commit install         # after M0.5
```

### 14.3 Running services (M2+)

```bash
docker compose up -d postgres redis otel-collector prometheus grafana
cd services/api && uvicorn app.main:app --reload
cd services/agents && python -m vibebite_agents.graph        # serves graph
cd services/mcp_server && python server.py                   # stdio
cd services/worker && celery -A app worker -l info
```

### 14.4 Seed data

`scripts/seed.py` (added in M1) creates: 3 users, 1 mission, 1 invite, 5 sample preferences, 10 cached places. Run with `python scripts/seed.py`.

### 14.5 Mobile dev build vs Expo Go

Google Maps SDK and Expo Notifications **require an Expo dev build** — they don't work in Expo Go. Use `eas build --profile development` to produce a dev client; install on device once, then `npx expo start --dev-client`.

---

## References

[^role]: The role description emphasizes AI agents, autonomous workflows, automation, reliability engineering, telemetry, incident analysis, and remediation systems — VibeBite's architecture demonstrates each.
[^places-overview]: Google Places API — establishment data and imagery for places.
[^places-textsearch]: Google Places Text Search — query-based place lookup with optional location bias.
[^places-details]: Google Places Place Details — full data for a known place ID.
[^otel]: OpenTelemetry — vendor-neutral framework for traces, metrics, and logs.
[^prom-alerting]: Prometheus alerting rules → Alertmanager (grouping, silencing, inhibition, notifications).
[^expo]: Expo — production-grade React Native framework.
[^eas]: EAS Build — produces App Store and Play Store binaries.
[^fastapi]: FastAPI — modern Python web framework using type hints.
[^pgvector]: pgvector — vector similarity search inside PostgreSQL.
[^langgraph-persistence]: LangGraph persistence — durable execution via saved workflow state.
[^langchain-hitl]: LangChain human-in-the-loop middleware — pauses execution for review of tool calls.
[^mcp]: Model Context Protocol — servers expose resources, prompts, and tools to AI clients.
