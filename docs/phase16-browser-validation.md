# Phase 16 — Browser & Operator Validation

**Date:** 2026-05-29  
**API:** `https://builddesk-api-149130710868.us-central1.run.app`  
**Revision:** `builddesk-api-00019-6p8` (image `3425c68`)  
**Frontend:** Vite dev (`http://localhost:5173`) with `VITE_API_BASE_URL` → live API (or `/api` proxy)

---

## CORS validation (automated)

Preflight against live health endpoint:

```bash
curl -s -I -X OPTIONS "$API/api/v1/health" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET"
```

**Result:** `200` with `access-control-allow-origin: http://localhost:5173` and credentials enabled.

Production hosting URL must be added to `ALLOWED_ORIGINS` on Cloud Run when a static frontend is deployed.

---

## Operator workflow matrix

| Workflow | Frontend surface | API validation | Browser status |
|----------|------------------|----------------|----------------|
| Register | `/register` | Live 201 + JWT | **Ready** — CORS OK for localhost |
| Login | `/login` | Live login | **Ready** |
| Dashboard / health | `/dashboard` | Health OK | **Ready** |
| Project creation | Dashboard → workspace | Staging script | **Ready** |
| Hierarchy authoring | `HierarchyPanel` | Staging script | **Ready** |
| Bulk units | `HierarchyPanel` bulk | 200 units live | **Ready** |
| Assemblies | `AssembliesPanel` + editor | Staging + load script | **Ready** |
| Package generation | `PackagesPanel` | GCS `gs://` ref live | **Ready** — PDF via API proxy |
| Revision flow | `PackagesPanel` | Staging rev ops | **Ready** |
| Approval workflow | Package transitions | Staging approve | **Ready** |
| Search | `SearchPanel` | Staging search | **Ready** |
| Exports | `ExportModal` | 3 exports staging | **Ready** — GCS-backed paths |
| Tenant branding | `TenantSettingsPanel` | Profile PUT/GET | **Ready** |
| PDF download | Package download action | PDF bytes via API | **Ready** (proxied GCS) |

---

## Usability notes

1. **Local dev:** Use `npm run dev` — Vite proxies `/api` to `VITE_API_BASE_URL`, avoiding CORS during development even without proxying.
2. **Direct browser → API:** Requires `ALLOWED_ORIGINS` to include the page origin (configured for `http://localhost:5173` on Cloud Run).
3. **PDF download:** GCS artifacts are streamed through authenticated API routes (no signed-URL key required on Cloud Run).
4. **Production frontend:** When hosted on a custom domain, add that origin to `ALLOWED_ORIGINS` and redeploy.

---

## Blockers / follow-ups

- [ ] Manual click-through on `localhost:5173` with live API (operator sign-off sheet)
- [ ] Add production frontend origin to Cloud Run env when static site URL is known
- [ ] Optional: minimal Playwright smoke for login → dashboard (deferred — API scripts cover backend)

---

## Recommended operator smoke (5 min)

1. `cd frontend && npm run dev`
2. Register new tenant at `/register`
3. Create project → add building/floor/types → bulk 20 units
4. Create kitchen assembly → generate package → download PDF
5. Confirm PDF opens and tenant branding appears on cover
