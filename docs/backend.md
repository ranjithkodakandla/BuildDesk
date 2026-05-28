# Backend Setup

## Local Development

Install dependencies:

pip install -r backend/requirements.txt

Run API:

uvicorn app.main:app --reload

Example endpoint:

GET /api/v1/health

## Environment

Uses:

* pydantic-settings
* .env support
* environment variables

## Deployment Target

Primary target:

GCP Cloud Run
