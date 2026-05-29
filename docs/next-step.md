# Next Step

> Auto-updated after each milestone. Always read this before starting a new session.

---

## Current State

| Field              | Value                                  |
|--------------------|----------------------------------------|
| Last completed phase | Phase 6 — Real Project Pilot Validation |
| Git branch         | `feat/phase-6-pilot-validation` (to be committed) |
| Test baseline      | 54/54 backend, 13/13 frontend |
| Migration state    | Up to date |

---

## Immediate Next Milestone

**Phase 7 — Asynchronous Package Generation & Cloud Storage**

Goal: Address the primary architectural bottleneck discovered in Phase 6. Move the synchronous PDF package generator into an asynchronous background task, and upload the resulting artifact to Google Cloud Storage (GCS).

Priority tasks:
1. **Background Tasks** — Migrate `POST /projects/{id}/package/generate` to use FastAPI `BackgroundTasks` (or Celery if complexity demands).
2. **Package Status Polling** — Ensure the frontend properly polls the `GET .../status` endpoint while the package is generating.
3. **GCS Integration** — Implement `CloudStorageService` to upload the generated PDF bytes to a storage bucket and return a signed URL.
4. **Database Update** — Add `storage_url` to the `ProjectPackageRecord`.

Domain test: Can a user trigger a massive 300-unit package generation, see a "Generating" loading state, and eventually download the PDF from a cloud bucket without timing out the HTTP request?

---

## Pending Blockers

- Need a GCP Service Account JSON key or local emulator (like fake-gcs-server) for testing cloud storage locally.

---

## Recommended Next Prompt

```
AUTONOMOUS IMPLEMENTATION MODE — Phase 7

Mandatory startup:
1. docs/session-start.md
2. docs/domain-guardrail.md
3. docs/current-state.md

PHASE 7 GOAL: Asynchronous Package Generation & Cloud Storage.

Upgrade the package workflow:
1. Move PDF generation to a background task.
2. Implement GCS upload (or local mock if no credentials).
3. Update the frontend to poll for status.

Domain test: Packages must generate asynchronously without blocking the API and deliver a secure URL.
If NO → reject and document in ADR rejection table.

Branch: feat/phase-7-async-packages
```
