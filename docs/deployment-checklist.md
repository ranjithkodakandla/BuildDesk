# Cloud Run Validation Checklist

Use this checklist to ensure that a newly deployed Cloud Run instance is fully operational and correctly configured.

### Phase 1: Build & Deploy
- [ ] **Build Success:** Docker image successfully builds (either locally or via Cloud Build).
- [ ] **Push Success:** Image is visible in Google Cloud Artifact Registry.
- [ ] **Deploy Success:** Cloud Run reports a successful revision rollout and provides a public service URL.
- [ ] **Startup Logs:** Backend type is correctly detected (e.g., "Starting BuildDesk with SQL Repository (postgres backend)").

### Phase 2: Health & Routing
- [ ] **Health Endpoint (`/api/v1/health`):**
  - Expected: `200 OK`
  - Validates `status: "ok"`
  - Validates `database: "sql-connected"` (If disconnected, check VPC/Firewall settings).
  - Validates `tenant_mode: true`.

### Phase 3: Application Functionality
- [ ] **Tenant Header Validation:**
  - `GET /api/v1/geometry/invalid-id` without `X-Tenant-ID` returns `422` (Missing header).
  - `GET /api/v1/geometry/invalid-id` with `X-Tenant-ID` returns `404` (Valid isolation).
- [ ] **Database Connectivity (CRUD):**
  - Create a shape (`POST /api/v1/geometry`).
  - Retrieve the created shape (`GET /api/v1/geometry/{id}`).
- [ ] **SVG Export Validation:**
  - Send a valid geometry payload to `POST /api/v1/export/svg`.
  - Ensure response is `image/svg+xml`.
- [ ] **PDF Export Validation:**
  - Send a valid geometry payload to `POST /api/v1/export/pdf`.
  - Ensure response is `application/pdf`.

### Phase 4: Troubleshooting
If any checks fail, review the Cloud Run logs:
```bash
make cloud-logs
```
