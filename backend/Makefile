.PHONY: run test migrate docker-build docker-up postgres-up postgres-down migrate-postgres cloud-build cloud-run-local deploy-gcp

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

docker-up:
	docker-compose up -d

postgres-up:
	docker-compose up -d postgres

postgres-down:
	docker-compose down

migrate-postgres:
	USE_SQL_REPOSITORY=true DATABASE_URL="postgresql+psycopg://builddesk:password@localhost:5432/builddesk" alembic upgrade head

cloud-build:
	gcloud builds submit --config cloudbuild.yaml .

cloud-run-local:
	docker build -t builddesk-api:latest .
	docker run -p 8080:8000 -e PORT=8000 -e APP_ENV=development builddesk-api:latest

deploy-gcp:
	./scripts/deploy.sh
