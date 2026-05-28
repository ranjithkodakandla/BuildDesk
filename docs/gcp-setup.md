# GCP Setup Guide

This guide details the steps required to prepare a Google Cloud Platform (GCP) project for deploying the BuildDesk backend.

## 1. Enable Required APIs

Run the following command to enable the necessary services on your GCP project:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

## 2. Artifact Registry Creation

Cloud Run deploys container images hosted in Artifact Registry. Create a Docker repository:

```bash
gcloud artifacts repositories create builddesk-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker repository for BuildDesk backend"
```

*Note: Ensure the location matches your intended Cloud Run deployment region.*

## 3. Secret Manager Preparation

Store sensitive configuration (like the Database URL) securely using Secret Manager.

```bash
echo -n "postgresql+psycopg://user:password@host/dbname" | gcloud secrets create builddesk-db-url --data-file=-
```

### Required Environment Variables

When deploying to Cloud Run, map these variables either as plain text or as secrets:

- `APP_ENV`: Set to `production`.
- `USE_SQL_REPOSITORY`: Set to `true` to use the Postgres backend.
- `DEBUG`: Set to `false`.
- `ALLOWED_ORIGINS`: Comma-separated list (e.g., `https://app.builddesk.example.com`).
- `DATABASE_URL`: **(Secret)** Mapped from Secret Manager.

## 4. Required IAM Roles

If using Cloud Build (`cloudbuild.yaml`), ensure the default Cloud Build Service Account has the following roles:
- **Cloud Run Admin** (`roles/run.admin`)
- **Service Account User** (`roles/iam.serviceAccountUser`)
- **Secret Manager Secret Accessor** (`roles/secretmanager.secretAccessor`) - *if accessing secrets during build.*

To grant Cloud Run access:
```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$PROJECT_NUMBER@cloudbuild.gserviceaccount.com" \
  --role="roles/run.admin"
```

## 5. Deployment Options

Once configured, you can deploy using:

1. **Local Script (Fastest for testing):**
   ```bash
   make deploy-gcp
   ```

2. **Cloud Build (CI/CD pattern):**
   ```bash
   make cloud-build
   ```
