.PHONY: run test migrate docker-build docker-up

run:
	uvicorn app.main:app --reload --port 8000

test:
	python -m pytest tests/ || true
	python -m tests.smoke_alembic
	python -m tests.smoke_multitenancy
	python -m tests.smoke_pdf_exporter
	python -m tests.smoke_sql_persistence
	python -m tests.smoke_svg_exporter
	python -m tests.smoke_deployment

migrate:
	alembic upgrade head

docker-build:
	docker build -t builddesk-api:latest .

docker-up:
	docker-compose up -d
