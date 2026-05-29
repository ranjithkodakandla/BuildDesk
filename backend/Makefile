.PHONY: run test migrate docker-build docker-up postgres-up postgres-down migrate-postgres cloud-build cloud-run-local deploy-gcp deploy-cloudsql check-health cloud-logs staging-validate

STAGING_URL ?= https://builddesk-api-149130710868.us-central1.run.app

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

deploy-cloudsql:
	@if [ -z "$$CLOUDSQL_INSTANCE" ]; then echo "Error: CLOUDSQL_INSTANCE is not set (e.g. project:region:instance)"; exit 1; fi
	./scripts/deploy.sh

check-health:
	@echo "Checking Cloud Run Health (ensure CLOUD_RUN_URL is set or defaults to localhost)..."
	curl -s $${CLOUD_RUN_URL:-http://localhost:8000}/api/v1/health | python -m json.tool

cloud-logs:
	@echo "Fetching recent Cloud Run logs..."
	gcloud run services logs read builddesk-api --region us-central1 --project stonedesk-app --limit 50

staging-validate:
	STAGING_API_URL=$(STAGING_URL) python scripts/run_staging_validation.py

check-staging-health:
	curl -s $(STAGING_URL)/api/v1/health | python -m json.tool
