# BuildDesk — Domain Guardrail
> **ADR-001 — Architecture Decision Record**
> **Status:** Active — enforced from Phase 3 onward
> **Authority:** All contributors, all milestones, all AI sessions

---

## The Rule

Before implementing any feature, validate against this single question:

> **Could this feature contribute toward generating a real fabrication package
> for a multifamily countertop project (similar to a real Canyon-style project PDF)?**

If the answer is **NO** → do not implement it. Document why it was rejected.

---

## What BuildDesk IS

BuildDesk is a **multifamily countertop fabrication package system**.

It exists to help fabrication shops (e.g. Canyon Surfaces) produce complete,
accurate, print-ready drawing packages for large multifamily construction projects.

### Primary use cases

| Domain | Examples |
|---|---|
| Project types | Multifamily apartment complexes, condo towers, mixed-use buildings |
| Clients | Builder / construction companies (Canyon-style) |
| Project structure | Optional Building → Floor → Unit → UnitType hierarchy |
| Assembly types | Kitchen, Vanity, Island, Bar Top, Laundry, ADA |
| Variants | MIR (mirror), ADA, LEFT, RIGHT, REV, Custom |
| Parts | Physical stone pieces with dimensions |
| Fabrication details | Edge treatments, cutouts, holes, splashes, seams |
| Output | Full project PDF drawing package — cover + type sheets + drawing pages + summary |

### What a real fabrication package looks like

```
Page 1:   Cover      — Project name, client, material, issue date, revision
Pages 2–N: Type Sheets — "Type A — Qty 8 — Units: 101, 102, 201, 202..."
           Assembly Drawings — dimensioned part layouts with cutouts, edges, seams
Last Page: Summary   — Total piece count, total sq ft, material quantities by type
```

---

## What BuildDesk is NOT

These descriptions of what we built before the domain realignment are **wrong abstractions**.
They must not guide future implementation decisions.

| ❌ Wrong framing | ✅ Correct framing |
|---|---|
| Simple geometry generator | Fabrication assembly modeller |
| Generic CAD demo | Project-specific drawing package generator |
| Rectangle drawing tool | Multi-part countertop layout engine |
| Single shape → one PDF | Full project → one PDF set |
| SVG playground | Fabrication drawing preview layer |
| Flat `project_id` UUID | Project → Building → Floor → Unit → UnitType hierarchy |
| `GeometryPiece` (area, perimeter) | Part with edge treatments, cutouts, holes, splashes |
| No concept of variants | MIR, ADA, LEFT/RIGHT, REV, Custom |

---

## Evaluation Checklist

When evaluating any proposed feature or task, ask these questions in order:

### 1. Domain Test
> Does this serve a real multifamily countertop fabrication workflow?

- ✅ YES → proceed to scoping
- ❌ NO → reject, document reason below

### 2. Hierarchy Test
> Is this feature aware of the correct domain hierarchy?

```
Tenant → Project → Building? → Floor? → UnitType → Unit (variant)
                                                      └─ Assembly → Part → {EdgeTreatment, Cutout, Hole, Splash, Seam}
```

- ✅ YES → proceed
- ❌ NO → fix the model before implementing

### 3. Package Test
> Does this feature contribute toward, or at least not contradict, generating a PDF package?

- ✅ YES → proceed
- ⚠️ NEUTRAL but necessary (auth, infra) → proceed with justification
- ❌ NO → reject

### 4. Reuse Test
> Does this reinvent something the geometry/SVG/PDF engine already does correctly?

- ✅ NO → proceed
- ⚠️ PARTIAL → wrap, don't replace
- ❌ YES, duplicates → reject or consolidate

---

## Rejection Log

| Date | Feature Proposed | Reason Rejected |
|---|---|---|
| — | *No rejections yet* | — |

> All future rejections must be logged here with date, proposed feature, and reason.

---

## Guardrail Inheritance Rules

This rule is **inherited by every future milestone, session, and contributor**.

1. Every new API endpoint must map to a real fabrication workflow step.
2. Every new domain model must correspond to a real entity a fabricator cares about.
3. Every new PDF/SVG output must be a page or drawing that could appear in a real package.
4. Every UI feature must serve someone in the builder/fabrication workflow (shop owner, estimator, drafter).
5. Infrastructure work (auth, DB, GCP) is exempt but must not be gold-plated — build only what the domain requires.

---

## Authoritative Domain Reference Documents

| Document | Purpose |
|---|---|
| `docs/domain-model-correction.md` | Full domain realignment ADR with concrete model definitions |
| `docs/architecture.md` | System architecture including corrected hierarchy and layer responsibilities |
| `docs/current-state.md` | Living milestone tracker |
| `docs/roadmap.md` | Phase-by-phase plan aligned to fabrication workflow |

---

## Quick Reference — Valid Next Features (Phase 3 onward)

These features **pass** the domain test. They may be implemented.

- `PackagePdfExporter` — multi-page PDF: cover, type sheets, assembly drawings, summary
- `PackageGeneratorService` — project → PDF orchestration with variant handling
- Assembly SVG preview (single assembly drawing)
- Project package versioning (Rev A, IFC, etc.)
- Part label system (A, B, C — fabrication convention)
- Cutout outlines in drawings (sink shapes, cooktop cutouts)
- Hole markers in drawings (faucet, soap)
- Edge treatment visual indicators
- Seam lines between parts
- Backsplash/splash dimensions in drawings
- Unit count and sq ft summary calculations
- Project creation wizard (UI)
- Assembly builder UI (part dimensions, cutouts, edges)
- Package download UI

## Quick Reference — Invalid Features

These features **fail** the domain test. They must NOT be implemented.

- Additional generic shape types (hexagon, custom polygon, etc.) with no fabrication mapping
- Generic CAD drawing tools
- Expanding the old `SHAPE_REGISTRY` with new shapes
- Generic geometry import/export (DXF, etc.) with no package integration
- Free-form annotation tools with no fabrication context
- Analytics dashboards not tied to material quantities or project status
- Any feature that treats a project as a single drawing rather than a multi-unit package
