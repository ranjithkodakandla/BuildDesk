# Domain Fidelity Recovery Report

**Branch:** `feat/reference-pdf-validation`  
**Date:** 2026-05-29  
**Prior verdict:** NO-GO ([`reference-pdf-validation.md`](./reference-pdf-validation.md))  
**Updated verdict:** **CONDITIONAL GO** (persistence recovered; shop-sheet parity still incomplete)

---

## 1. Root cause analysis (proved)

### Symptom

`POST /api/v1/assemblies` returned **HTTP 500** on production (Cloud SQL / PostgreSQL) whenever `parts[].edges` or `parts[].cutouts` was non-empty. Bare parts (no nested rows) returned **201**.

### Reproduction

| Environment | Edges + cutouts |
|-------------|-----------------|
| SQLite in-memory (default tests, FK off) | Pass (masks bug) |
| SQLite with `PRAGMA foreign_keys=ON` | **IntegrityError** before fix |
| Live Cloud Run (PostgreSQL) | **HTTP 500** before fix |

### Exact cause

`FabricationRepository.save_assembly()` inserted child rows (`edge_treatments`, `cutouts`, …) in the **same SQLAlchemy flush** as parent `parts` rows **without flushing the parent first**.

PostgreSQL enforces foreign keys at commit/flush time. Child `part_id` FK references did not yet exist → `IntegrityError` → unhandled **500**.

**Not** missing migrations (tables exist). **Not** enum mismatch (422 would occur first). **Not** schema drift on `edge_treatments`.

### Proof after fix

```
edge create 201
get 200 edges 1
```

Full Bull Outdoor seed with 6 parts, 24+ edges, 1 sink cutout: **201** + package PDF generated (10,701 bytes).

---

## 2. Fix implemented

**File:** `backend/app/repositories/fabrication_repository.py`

1. `session.flush()` after assembly header fields are set (before deletes/inserts).  
2. `session.flush()` after each `PartRecord` insert, **before** edge/cutout/hole/splash children.

**Deployed:** Cloud Run `builddesk-api-00021-br6` (image `53d66dd` + working-tree fix in build context).

---

## 3. Tests added

| Test | Purpose |
|------|---------|
| `tests/test_fabrication_fk_order.py` | SQLite **with FK enforced** — edge + cutout round-trip |
| Existing `tests/test_fabrication.py::test_create_complex_assembly` | Unchanged; still passes |

**Baseline:** **77/77** pytest (was 76 + 1 new).

---

## 4. Revalidation (real fabrication metadata)

**Command:**

```bash
cd backend && source .venv/bin/activate && python scripts/seed_bull_outdoor_reference.py
```

**Result:** Success — 6 parts with edges, sink cutout on piece 1, package **100-01**, GCS PDF stored.

**Manifest:** `artifacts/reference-validation/reference_seed_manifest.json`

| Field | Value |
|-------|--------|
| Email | `bull_ref_6d76d45a@builddesk.accept` |
| Password | `BullOutdoorRef123!` |
| Tenant | `4b2b3a2c-cdfc-40b3-b057-8754c0bb8960` |
| Project | `a4342197-ba59-44b2-9a95-04bb00176c90` |
| Workspace | https://builddesk-web-149130710868.us-central1.run.app/projects/a4342197-ba59-44b2-9a95-04bb00176c90 |

---

## 5. Visible browser validation (operator-run)

Playwright is configured for **headed** mode (`headless: false`, `slowMo: 400`).

**Run on your machine (you will see the browser):**

```bash
cd frontend
npm install
npx playwright install chromium

export REF_VALIDATION_EMAIL="bull_ref_6d76d45a@builddesk.accept"
export REF_VALIDATION_PASSWORD="BullOutdoorRef123!"
export REF_VALIDATION_TENANT="4b2b3a2c-cdfc-40b3-b057-8754c0bb8960"
export REF_VALIDATION_PROJECT_ID="a4342197-ba59-44b2-9a95-04bb00176c90"
export FRONTEND_URL="https://builddesk-web-149130710868.us-central1.run.app"

npx playwright test e2e/reference-bull-outdoor-headed.spec.ts --headed --workers=1
```

**Narrated flow:** login → open seeded project → assemblies tab (6 parts, edge notes) → assembly editor → packages → download PDF.

**Note:** UI assembly editor still uses `front/back/left/right` positions (not drawing `top/bottom`). Data model matches API; Virgin sheet uses plan-view bottom/top — map via front/back when entering.

---

## 6. Reference delta (post-recovery)

Compare: `artifacts/reference-pdf/page-1.png` vs `artifacts/reference-validation/builddesk-recovery-page-4.png`

| Category | Before recovery | After recovery | vs reference |
|----------|-----------------|----------------|--------------|
| Edge persistence (API) | **FAIL** (500) | **FIXED** (201 + round-trip) | Data only |
| Cutout / sink persistence | **FAIL** | **FIXED** | **IMPROVED** — sink drawn on PART A |
| Edge schedule in PDF notes | Missing | **IMPROVED** — LEFT/FRONT polished, RAW sides listed | Partial |
| Cutout schedule in PDF | Missing | **IMPROVED** — 17.5×17.5 @ offsets | Partial |
| Polished vs raw linework | N/A | **IMPROVED** — thick/thin edges | Partial (no X symbol) |
| Single-sheet 6-piece layout | FAIL | **STILL MISSING** | FAIL |
| Inch + mm dimensions | FAIL | **STILL MISSING** | FAIL |
| Legend (X, RAW, BS, SS) | FAIL | **STILL MISSING** (minimal line legend only) | FAIL |
| Grain arrows | FAIL | **STILL MISSING** (text notes only) | FAIL |
| R1/2, break corners | FAIL | **STILL MISSING** (text notes only) | FAIL |
| Virgin title block | FAIL | **STILL MISSING** | FAIL |
| Cover total parts / sq ft | 0 / 0 bug | **STILL MISSING** (verify on next package) | FAIL |

---

## 7. Reprioritized backlog (no auto-implement)

### Critical

1. Package cover **part count / sq ft** accuracy in manifest summary.  
2. **Single-sheet shop layout** (6 pieces positioned like reference 100-01).  
3. **Legend system** (X, RAW, BS, SS, TR, F).  
4. **Dual inch/mm** dimension strings.  

### Important

5. Grain direction arrows on drawing.  
6. Corner notation (R1/2, R1/8, break corners) as graphics/leaders.  
7. Virgin-style **title block** strip.  
8. UI assembly editor: edge position labels aligned with shop drawing vocabulary.  

### Nice-to-have

9. Oversized-part rectangle on dimensions.  
10. Community vs program name fields.  
11. Sheet-level **QTY=45** on drawing face.  

---

## 8. Updated verdict

| Verdict | **CONDITIONAL GO** |
|---------|-------------------|
| Why not GO | Output PDF is still not a Virgin/Canyon shop sheet; layout/legend/notation remain far from reference. |
| Why not NO-GO | **Core fabrication data path works in production** — edges, cutouts, sink, package generation, PDF shows cutout + edge schedules. |
| Operator action | Run headed Playwright command above; confirm UI save of edges/cutouts in assembly editor against live API. |

---

## Files changed (recovery)

- `backend/app/repositories/fabrication_repository.py` — flush ordering  
- `backend/tests/test_fabrication_fk_order.py` — FK-enforced regression test  
- `backend/scripts/seed_bull_outdoor_reference.py` — full 6-piece nested payload  
- `frontend/src/api/assemblies.ts` — list unwrap (workspace crash)  
- `frontend/e2e/reference-bull-outdoor-headed.spec.ts` — visible replay  
- `frontend/playwright.config.ts` — headed defaults  
