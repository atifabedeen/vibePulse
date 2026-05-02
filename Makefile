.PHONY: up down logs psql sqlite migrate seed clean

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

psql:
	docker compose exec postgres psql -U vibebite -d vibebite

# Open the local SQLite dev DB (created by `make migrate` when DATABASE_URL
# points at sqlite+aiosqlite:///./vibebite.db).
sqlite:
	sqlite3 services/api/vibebite.db

migrate:
	cd services/api && alembic upgrade head

seed:
	cd services/api && python -m app.scripts.seed

clean:
	docker compose down -v
