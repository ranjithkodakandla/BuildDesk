#!/usr/bin/env bash
# Deploy BuildDesk frontend to Cloud Run (static nginx + SPA routing)
set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT_ID=${GCP_PROJECT_ID:-stonedesk-app}
REGION=${GCP_REGION:-us-central1}
SERVICE_NAME=${GCP_SERVICE_NAME:-builddesk-web}
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IMAGE_TAG=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo "local")
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/builddesk-repo/${SERVICE_NAME}:${IMAGE_TAG}"

echo "Building production bundle..."
npm run build

echo "Building container (linux/amd64)..."
docker build --platform linux/amd64 -t "$IMAGE_URL" .

echo "Pushing image..."
docker push "$IMAGE_URL"

echo "Deploying Cloud Run service ${SERVICE_NAME}..."
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URL" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --quiet

URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID" --format='value(status.url)')
echo "Frontend deployed: $URL"
echo "Update Cloud Run API ALLOWED_ORIGINS to include: $URL"
