# GCP Live Deployment Notes

## Summary of Operations

On the initial deployment attempt of the BuildDesk backend to GCP Cloud Run, several environmental challenges were identified and mitigated, proving the resilience of the deployment scripts.

### 1. Cloud Build vs. Local Build
An attempt to run `make cloud-build` utilizing the `cloudbuild.yaml` failed because the default Cloud Build Service Account lacked the `roles/logging.logWriter` permission, causing it to fail immediately upon execution (Error 125).

**Fix applied:** Bypassed Cloud Build for this initial smoke test and utilized the local deployment shell script (`scripts/deploy.sh`) directly via `make deploy-gcp`.

### 2. Artifact Registry Project Targeting
The default `deploy.sh` script utilized `my-gcp-project` as the default project ID fallback.
**Fix applied:** Explicitly passed the target environment variable `GCP_PROJECT_ID=stonedesk-app` to ensure the local docker push targeted the correct remote Artifact Registry.

### 3. Architecture Compatibility
The initial local docker build pushed a `linux/arm64` image because it was built on a Mac Apple Silicon machine. Cloud Run rejected this image with the error:
`Container manifest type 'application/vnd.oci.image.index.v1+json' must support amd64/linux.`

**Fix applied:** Updated `scripts/deploy.sh` to explicitly force the docker build targeting the cloud architecture:
```bash
docker build --platform linux/amd64 -t "$IMAGE_URL" .
```
This ensured the resulting container was compliant with Cloud Run's requirements.

### Final Working Configuration

**Deployment Command:**
```bash
GCP_PROJECT_ID=stonedesk-app make deploy-gcp
```

**Service URL:**
https://builddesk-api-149130710868.us-central1.run.app

### Validated Endpoints

All endpoints successfully passed validation in the live environment:
- `GET /api/v1/health` returned `{status: ok, database: sql-connected, tenant_mode: true}`
- `POST /api/v1/geometry` successfully created geometry records using the `X-Tenant-ID` header.
- `GET /api/v1/geometry/{id}` successfully rejected unauthenticated tenants with a `404 Not Found`.
- `POST /api/v1/export/svg` produced a valid `image/svg+xml`.
- `POST /api/v1/export/pdf` produced a valid `application/pdf` document.
