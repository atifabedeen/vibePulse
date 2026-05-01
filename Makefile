.PHONY: up down logs psql migrate seed clean

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

psql:
	docker compose exec postgres psql -U vibebite -d vibebite

migrate:
	cd services/api && alembic upgrade head

seed:
	cd services/api && python -m app.scripts.seed

clean:
	docker compose down -v
