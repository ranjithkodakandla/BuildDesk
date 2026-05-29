# BuildDesk — Milestone Template
> Copy this template for every new milestone. Fill in every section before writing code.
> A milestone is not complete until: code is committed + tests pass + `docs/current-state.md` and `docs/next-step.md` are updated.

---

## Milestone Header

| Field | Value |
|---|---|
| **Milestone Name** | Phase N — [Name] |
| **Phase** | N |
| **Target Branch** | `feat/phase-N-[slug]` |
| **Estimated Effort** | N days |
| **Date Started** | YYYY-MM-DD |
| **Date Completed** | YYYY-MM-DD |
| **Commit SHA** | (fill after commit) |

---

## Section 1 — Domain Validation (MANDATORY — complete before any code)

### 1.1 Domain Test
> Could this milestone contribute toward generating a real fabrication package for a multifamily countertop project?

**Answer:** [ YES / NO ]

**Justification:**
```
[Explain exactly how this milestone contributes to the real fabrication workflow.
 If NO, stop here. Do not implement. Log in docs/domain-guardrail.md.]
```

### 1.2 Hierarchy Alignment Check
> Does this milestone operate correctly within the domain hierarchy?

```
Tenant → Project → Building? → Floor? → UnitType → Unit (variant)
                                                      └─ Assembly → Part → {EdgeTreatment, Cutout, Hole, Splash, Seam}
```

**Answer:** [ ALIGNED / NOT ALIGNED ]

**Which hierarchy levels does this milestone touch?**
```
□ Tenant        □ Project       □ Building      □ Floor
□ UnitType      □ Unit          □ Assembly      □ Part
□ EdgeTreatment □ Cutout        □ Hole          □ Splash
□ Seam          □ FabricationNote               □ ProjectPackage
```

**Notes:**
```
[Describe how this milestone interacts with the hierarchy. Any new levels introduced?]
```

### 1.3 Package Alignment Check
> Does this milestone contribute toward, or at least not contradict, generating a PDF package?

**Answer:** [ CONTRIBUTES / NEUTRAL+JUSTIFIED / CONTRADICTS ]

**Which package output elements does this milestone enable or improve?**
```
□ Cover page                □ Type sheets
□ Assembly drawing pages    □ Summary page
□ Assembly SVG preview      □ Package versioning
□ Material quantities        □ Part labels
```

**Notes:**
```
[Describe the connection to the package output. If NEUTRAL, justify why it's still necessary.]
```

### 1.4 Reuse vs Drift Analysis
> Does this milestone reuse existing correct subsystems, or does it risk drifting into wrong abstractions?

**Reuse plan:**
| Subsystem | Files | Action |
|---|---|---|
| Geometry Primitives | `geometry/primitives.py` | KEEP / WRAP / REPLACE |
| SVG Exporter | `exporters/svg_exporter.py` | KEEP / WRAP / REPLACE |
| PDF Exporter | `exporters/pdf_exporter.py` | KEEP / WRAP / REPLACE |
| JWT Auth | `app/auth/` | KEEP / WRAP / REPLACE |
| Repository Pattern | `app/repositories/` | KEEP / EXTEND / REPLACE |
| FabricationService | `app/services/fabrication_service.py` | KEEP / EXTEND / REPLACE |

**Drift risks identified:**
```
[List any specific risks that this milestone could introduce incorrect abstractions.
 How are they mitigated?]
```

---

## Section 2 — Scope Definition

### 2.1 Deliverables (what gets committed)

```
□  Domain models:   app/models/[module].py
□  ORM records:     app/db/models.py  (additive only)
□  Migration:       alembic/versions/[hash]_[description].py
□  Repository:      app/repositories/[module]_repository.py
□  Service:         app/services/[module]_service.py
□  API router:      app/api/[module].py
□  API schemas:     app/api/[module]_schemas.py
□  Tests:           backend/tests/test_[module].py
□  Docs updated:    docs/current-state.md
□  Docs updated:    docs/next-step.md
□  Docs updated:    docs/architecture.md  (if architecture changed)
```

### 2.2 New API Endpoints

| Method | Path | Purpose |
|---|---|---|
| — | — | — |

### 2.3 New Database Tables / Columns

> **Rule: All migrations are ADDITIVE ONLY. No DROP. No RENAME.**

| Table | Action | Notes |
|---|---|---|
| — | ADD TABLE / ADD COLUMN | — |

### 2.4 Out of Scope (explicitly excluded)

```
[List anything that might seem related but is deliberately NOT in this milestone.
 This prevents scope creep.]
```

---

## Section 3 — Test Plan

### 3.1 Smoke Test Targets

| Test | Expected Result |
|---|---|
| — | — |

### 3.2 Baseline (must remain green)
- Previous test count before this milestone: **N / N passing**
- Expected test count after: **N / N passing**

---

## Section 4 — Completion Checklist

Fill in after implementation:

```
□  All deliverables from Section 2.1 committed
□  All new API endpoints return correct status codes
□  Alembic migration applied cleanly (no errors)
□  All smoke tests passing
□  No regressions in existing tests
□  docs/current-state.md updated with new ✓ items
□  docs/next-step.md updated to point to the NEXT milestone
□  Committed to git with descriptive message following convention:
       feat([module]): implement Phase N [Name]
□  Pushed to origin
□  (If applicable) Deployed and validated on GCP Cloud Run + Cloud SQL
```

---

## Section 5 — Post-Milestone Notes

```
[Anything discovered during implementation that affects future milestones.
 Decisions made. Trade-offs accepted. Known debt introduced.]
```

---

## Commit Message Convention

```
feat([module]): implement Phase N [Name]

- [Bullet: what domain model was added/changed]
- [Bullet: what ORM/migration was applied]
- [Bullet: what service logic was implemented]
- [Bullet: what API endpoints were exposed]
- [Bullet: test count and results]
- [Bullet: GCP validation status if applicable]
```

---

## Example: Phase 3 filled out

### 1.1 Domain Test
**Answer:** YES
**Justification:** The package generator produces the primary deliverable — a multi-page PDF fabrication drawing set. This is literally the document that fabricators use to cut stone. It is the core output of BuildDesk.

### 1.2 Hierarchy Alignment Check
**Answer:** ALIGNED
**Levels touched:** Project, UnitType, Unit, Assembly, Part, Splash, Cutout, Hole, EdgeTreatment, FabricationNote

### 1.3 Package Alignment Check
**Answer:** CONTRIBUTES
**Enables:** Cover page, Type sheets, Assembly drawing pages, Summary page, Material quantities

### 1.4 Reuse Analysis
- Geometry Primitives → KEEP (used by drawing pages)
- SVG Exporter → WRAP (assembly preview)
- PDF Exporter → WRAP (add PackagePdfExporter alongside existing)
- JWT Auth → KEEP
- Repository Pattern → EXTEND (add PackageRepository)
