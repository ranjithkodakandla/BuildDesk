#!/usr/bin/env bash
# deployment script for GCP Cloud Run

set -e

# Default variables
PROJECT_ID=${GCP_PROJECT_ID:-"my-gcp-project"}
REGION=${GCP_REGION:-"us-central1"}
REPO_NAME=${GCP_REPO_NAME:-"builddesk-repo"}
SERVICE_NAME=${GCP_SERVICE_NAME:-"builddesk-api"}
IMAGE_TAG=$(git rev-parse --short HEAD)
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "🚀 Deploying BuildDesk Backend to GCP Cloud Run"
echo "Project: $PROJECT_ID | Region: $REGION"
echo "Image:   $IMAGE_URL"
echo "------------------------------------------------"

# 1. Build the image
echo "🔨 Building Docker image for Cloud Run (linux/amd64)..."
docker build --platform linux/amd64 -t "$IMAGE_URL" .

# 2. Push the image
echo "☁️ Pushing to Artifact Registry..."
docker push "$IMAGE_URL"

# 3. Deploy
echo "🚢 Deploying to Cloud Run..."
CLOUDSQL_ARGS=""
if [ -n "$CLOUDSQL_INSTANCE" ]; then
  CLOUDSQL_ARGS="--add-cloudsql-instances $CLOUDSQL_INSTANCE"
  echo "Linking Cloud SQL Instance: $CLOUDSQL_INSTANCE"
fi

gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URL" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --platform managed \
  --allow-unauthenticated \
  $CLOUDSQL_ARGS \
  --set-env-vars APP_ENV=production,USE_SQL_REPOSITORY=true,USE_LOCAL_STORAGE=false \
  --set-secrets DATABASE_URL=BUILDDESK_DATABASE_URL:latest,JWT_SECRET_KEY=BUILDDESK_JWT_SECRET:latest \
  --quiet

echo "✅ Deployment completed successfully!"
