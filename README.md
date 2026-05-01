# VibeBite

> Find the food spot your whole group can actually agree on.

VibeBite is a mobile AI agent app that collects group food preferences,
searches nearby restaurants, ranks them by vibe and constraints, explains
tradeoffs, runs a group vote, picks a winner and a backup, and replans
when the group changes its mind.

**Status:** WIP — design phase. M0 (repo scaffold) in progress.
**License:** UNLICENSED — private project.

## Repository

The local working directory is named `vibePulse` for historical reasons;
the canonical project name is **VibeBite**. The monorepo root in the
spec is `vibebite/`.

## What's here

- [`implementation.md`](./implementation.md) — full build spec: product,
  data model, REST API, LangGraph workflow, MCP server, observability,
  security, testing, and milestone roadmap.
- [`.env.example`](./.env.example) — every environment variable the spec
  references. Copy to `.env` and fill in locally.

The service code (`services/`, `apps/`, `infra/`) lands in M1+; see the
roadmap in `implementation.md` sec 13.

## Tech stack at a glance

Mobile: React Native + Expo + TypeScript.
Backend: Python 3.9, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 +
pgvector, Redis 7, Celery/Dramatiq.
Agents: LangGraph + OpenAI, MCP server.
Ops: OpenTelemetry, Prometheus, Grafana, Docker, GitHub Actions.

## Local setup (M0)

```bash
git clone git@github.com:atifabedeen/vibePulse.git
cd vibePulse
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Service-by-service run instructions land with each milestone — see
`implementation.md` sec 14.
