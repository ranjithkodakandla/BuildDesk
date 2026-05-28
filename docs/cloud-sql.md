# Cloud SQL PostgreSQL Integration

This document outlines the workflow for creating, configuring, and connecting to a durable Google Cloud SQL PostgreSQL instance for the BuildDesk backend.

## 1. Instance Creation
Create a new PostgreSQL 15+ instance. For development and lightweight demo purposes, it is highly recommended to use the `db-f1-micro` tier to minimize costs.

```bash
gcloud sql instances create builddesk-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --storage-type=HDD \
    --storage-size=10GB
```

## 2. Database and User Setup
Once the instance is available, create the required database and user:

```bash
# Create the database
gcloud sql databases create builddesk --instance=builddesk-db

# Create a user and set a strong password
gcloud sql users create builddesk_user \
    --instance=builddesk-db \
    --password="YOUR_STRONG_PASSWORD"
```

## 3. Networking and Connections
Cloud Run services typically connect to Cloud SQL securely through the **Cloud SQL Auth Proxy** via Unix sockets, or via Direct VPC Egress (Private IP).

For standard Cloud Run connectivity via Unix sockets, you must link the Cloud SQL connection string to the Cloud Run service during deployment.

**Connection String Pattern:**
```text
postgresql+psycopg://builddesk_user:YOUR_STRONG_PASSWORD@/builddesk?host=/cloudsql/YOUR_PROJECT_ID:us-central1:builddesk-db
```

## 4. Secret Manager Integration
Never commit the `DATABASE_URL` to source control. Use Google Secret Manager to inject the database URL at runtime.

**Create the secret:**
```bash
echo -n "postgresql+psycopg://builddesk_user:YOUR_STRONG_PASSWORD@/builddesk?host=/cloudsql/YOUR_PROJECT_ID:us-central1:builddesk-db" \
  | gcloud secrets create BUILDDESK_DATABASE_URL --data-file=-
```

**Grant Access:**
Ensure your Cloud Run Service Account has the `Secret Manager Secret Accessor` role.

## 5. Deployment Workflow
To deploy Cloud Run and link the Cloud SQL instance, update the `deploy.sh` script or Cloud Build configuration to include the `--add-cloudsql-instances` flag and inject the secret.

```bash
gcloud run deploy builddesk-api \
    --image=us-central1-docker.pkg.dev/... \
    --add-cloudsql-instances=YOUR_PROJECT_ID:us-central1:builddesk-db \
    --set-secrets=DATABASE_URL=BUILDDESK_DATABASE_URL:latest
```

## 6. Migration Execution
To run Alembic migrations against the live Cloud SQL instance, you have two common options:
1. **Cloud SQL Proxy**: Run the proxy locally to expose a local port `5432`, then run `make migrate-postgres`.
2. **Cloud Build Job**: Execute the migration within the VPC or Cloud Build environment using the same securely injected secrets.
