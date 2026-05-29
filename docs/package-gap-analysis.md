# Package Gap Analysis — Phase 4 Source of Truth

> **ADR-001 compliant.** This document is the authoritative record of BuildDesk's current
> fabrication package fidelity versus real multifamily countertop fabrication PDF expectations.
> All Phase 4 implementation decisions must reference this document.
>
> **Evaluated:** Phase 3 output (`d7db7e6`)
> **Target:** Real Canyon-style multifamily countertop fabrication package

---

## Evaluation Legend

| Symbol | Meaning |
|--------|---------|
| ✅ MATCH | Output meets fabrication standard |
| ⚠️ PARTIAL | Feature exists but missing fidelity detail |
| ❌ MISSING | Feature absent; fabricator cannot use output |

---

## 1. Cover Page

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Project name | ✅ MATCH | Rendered large, legible | — |
| Client name | ✅ MATCH | Present | — |
| Material specification | ✅ MATCH | Present | — |
| Issue date | ✅ MATCH | Present | — |
| Revision / version | ✅ MATCH | Badge rendered | — |
| Address / project location | ✅ MATCH | Present | — |
| Project status | ✅ MATCH | Draft / In Progress / Issued | — |
| Prepared by / company stamp | ❌ MISSING | No "Prepared by: Canyon Surfaces" block | Add issued_by block with shop name |
| Sheet count callout | ❌ MISSING | Cover does not state total page count | Add "Sheets: N" callout |
| Logo / branding area | ⚠️ PARTIAL | "BUILDDESK" text only; no logo placeholder | Acceptable for Phase 4 |
| Cover drawing / thumbnail | ❌ MISSING | Real packages often include a site plan thumbnail | Deferred — no CAD input |

**Cover Score: 6/11 elements at MATCH or acceptable PARTIAL**

---

## 2. Type Sheet (Unit Grouping)

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Unit type code (A, B, C) | ✅ MATCH | Prominent code header | — |
| Qty count (Qty: 8) | ✅ MATCH | Present in header | — |
| Unit list (101, 102, 201…) | ✅ MATCH | Comma-separated list | — |
| Variant badge (MIR, ADA) | ✅ MATCH | Coloured badge rendered | — |
| Assembly type list | ✅ MATCH | Kitchen, Vanity etc listed | — |
| Base type reference (A-MIR → A) | ❌ MISSING | No "derived from Type A" reference | Add base_type link if present |
| Square footage per type | ❌ MISSING | Total sq ft for this type group not shown | Compute and display |
| Part count per type | ❌ MISSING | Piece count not shown on type sheet | Compute from assemblies |
| Assembly thumbnail diagram | ❌ MISSING | Real packages show a mini layout diagram | **Phase 4 KEY ITEM** — add scaled thumbnail |
| Notes field per type | ❌ MISSING | No per-type fabrication notes | Add notes from unit type description |

**Type Sheet Score: 5/10 at MATCH**

---

## 3. Assembly Drawing Page — Layout & Composition

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Title block (type, assembly type, variant) | ✅ MATCH | In page header | — |
| Part letter labels (A, B, C) | ✅ MATCH | Text rendered | — |
| Part dimensions text | ✅ MATCH | L × D × T rendered | — |
| **Scaled part outline (rectangle)** | ❌ MISSING | **Parts are text tables only — no actual drawing** | **Phase 4 CRITICAL** |
| **Dimension leader lines with arrows** | ❌ MISSING | **No vector callout lines** | **Phase 4 CRITICAL** |
| Drawing zone vs notes zone split | ❌ MISSING | No two-column layout | Add split: drawing left, notes right |
| Part area calculation visible | ⚠️ PARTIAL | Shown in text "(Area: X sq ft)" | Keep; add to drawing |
| North/orientation indicator | ❌ MISSING | Not applicable for countertops (no N arrow needed) | Reject — not a countertop convention |
| Scale indicator | ❌ MISSING | No "Scale: 1"=4'" callout | Add scale note |
| Page number in title block | ⚠️ PARTIAL | In footer only; not in title block | Add to header |

**Layout Score: 3/10 at MATCH — PRIMARY GAP**

---

## 4. Edge Representation

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Edge type list per part | ✅ MATCH | Text: "FRONT: Eased  BACK: Raw" | — |
| **Visual edge differentiation on drawing** | ❌ MISSING | **No visual distinction on part outline** | **Phase 4 CRITICAL** — thick/coloured lines per edge |
| Polished edge indicator | ❌ MISSING | Should be bold/double line on drawing | Implement: thick stroke for polished |
| Raw/unfinished edge indicator | ❌ MISSING | Should be thin/dashed on drawing | Implement: dashed for raw |
| Miter edge indicator | ❌ MISSING | Should be diagonal line indicator | Implement |
| Edge length callout | ⚠️ PARTIAL | Length in text only | Add length on edge line |
| Edge legend on drawing page | ❌ MISSING | No legend box explaining line types | Add legend block |

**Edge Score: 1/7 at MATCH — CRITICAL GAP**

---

## 5. Cutout Representation

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Cutout text description | ✅ MATCH | Type, mount, dims, center listed | — |
| **Scaled cutout rectangle on drawing** | ❌ MISSING | **No visual outline in part drawing zone** | **Phase 4 CRITICAL** |
| Cutout type label on drawing | ❌ MISSING | No "SINK" / "COOKTOP" text in drawing | Add centred label in cutout rect |
| Mount type annotation | ❌ MISSING | No undermount/overmount visual distinction | Add: dashed = undermount, solid = overmount |
| Center dimension callouts | ❌ MISSING | No leader lines from part edge to cutout center | Add X and Y offset callouts |
| Cutout radius corners (sink) | ❌ MISSING | Real sinks have radiused corners | Implement rounded rect for sink cutouts |
| Reveal dimension | ❌ MISSING | Undermount reveal not shown | Deferred — Phase 5 |

**Cutout Score: 1/7 at MATCH — CRITICAL GAP**

---

## 6. Hole Representation

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Hole text description | ✅ MATCH | Purpose, diameter, center listed | — |
| **Scaled hole circle on drawing** | ❌ MISSING | **No visual circle in part drawing** | **Phase 4 CRITICAL** |
| Hole label (Faucet, Soap) | ❌ MISSING | No label on drawing | Add purpose label near circle |
| Diameter callout | ❌ MISSING | No "Ø 1⅜"" callout | Add callout |
| Hole group spacing | ❌ MISSING | Multi-hole faucet sets not shown as group | Deferred |

**Hole Score: 1/5 at MATCH — CRITICAL GAP**

---

## 7. Splash Representation

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Splash text description | ✅ MATCH | Type and dims listed | — |
| **Splash visual band on drawing** | ❌ MISSING | **No shaded band along edge** | **Phase 4 CRITICAL** |
| Backsplash height callout | ❌ MISSING | No "4" BSP" dimension on drawing | Add |
| Side splash annotation | ❌ MISSING | Left/right splashes not visually distinct | Implement |
| Splash material match note | ❌ MISSING | "Same material" vs "different" not shown | Deferred |

**Splash Score: 1/5 at MATCH — CRITICAL GAP**

---

## 8. Seam Indicators

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Seam lines between parts | ❌ MISSING | Parts have no seam line showing join | Add dashed vertical line between adjacent parts |
| Seam type (butt, mitre, etc.) | ❌ MISSING | Not in domain model or drawing | Add as future Phase 5 |
| Seam location dimension | ❌ MISSING | No dimension callout for seam position | Deferred |

**Seam Score: 0/3 — MISSING (partial implementation in Phase 4)**

---

## 9. Variant Handling

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| MIRROR badge on type sheet | ✅ MATCH | Present | — |
| ADA badge on type sheet | ✅ MATCH | Present | — |
| MIRROR badge on drawing page title | ✅ MATCH | In header | — |
| Mirror geometry flip on drawing | ❌ MISSING | Drawing not geometrically mirrored | Implement X-flip for MIR assemblies |
| ADA visual notation on drawing | ❌ MISSING | No ADA indicator symbol on drawing | Add ADA symbol / callout |
| Variant inherited from unit | ✅ MATCH | Service logic handles it | — |

**Variant Score: 3/6 at MATCH**

---

## 10. Qty / Unit Presentation

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Qty shown on type sheet | ✅ MATCH | "Qty: 8" in header | — |
| Unit list shown on type sheet | ✅ MATCH | Comma-separated | — |
| Qty on assembly drawing page header | ✅ MATCH | "Qty: N" present | — |
| Per-building / per-floor breakdown | ❌ MISSING | No building/floor grouping on type sheet | Phase 5 |

**Qty Score: 3/4 at MATCH**

---

## 11. Page Layout & Title Block

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Consistent page header | ✅ MATCH | Dark band, project name, title | — |
| Consistent footer with page ref | ✅ MATCH | Line + confidential + version | — |
| Drawing zone / notes zone split | ❌ MISSING | No two-column layout on drawing pages | Add: ~60% drawing, ~40% notes column |
| Title block (standard engineering TB) | ❌ MISSING | No formal title block (project/revision/scale/sheet) | Add simplified fabrication title block |
| Sheet number in header | ❌ MISSING | Page number only in footer | Add "Sheet N of M" to header |
| Revision block | ❌ MISSING | No revision history table | Deferred — Phase 6 |

**Layout Score: 2/6 at MATCH**

---

## 12. Fabrication Notes

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Assembly-level notes rendered | ✅ MATCH | Notes rendered in red | — |
| Notes zone placement | ❌ MISSING | Notes in text stream; should be in dedicated zone | Move to right-side notes column |
| Part-level notes | ✅ MATCH | Present in text | — |
| "SEE NOTE N" callout references | ❌ MISSING | No callout balloon system | Deferred — complex |
| Critical note highlight (box) | ❌ MISSING | Red text only; real packages box critical notes | Add bordered box for notes |

**Notes Score: 2/5 at MATCH**

---

## 13. Summary Page

| Element | Status | Gap Description | Phase 4 Action |
|---|---|---|---|
| Total units | ✅ MATCH | Present | — |
| Total assemblies | ✅ MATCH | Present | — |
| Total parts (pieces) | ✅ MATCH | Present | — |
| Total sq ft | ✅ MATCH | Present | — |
| Assembly breakdown by type | ✅ MATCH | Kitchen: N, Vanity: N | — |
| Unit type breakdown | ✅ MATCH | Type A: 8, Type B: 4 | — |
| Material quantities by piece type | ❌ MISSING | No "Main Top: 16 pieces, Splash: 8" breakdown | Add part_counts_by_type rendering |
| Running footage (LF) for edges | ❌ MISSING | Total linear feet of polished edges not shown | Compute in Phase 4 |
| Material waste estimate | ❌ MISSING | No overage calculation | Deferred |

**Summary Score: 6/9 at MATCH**

---

## Overall Gap Summary

| Category | Score | Primary Phase 4 Action |
|---|---|---|
| Cover Page | 6/11 | Add issued_by, sheet count |
| Type Sheet | 5/10 | Add thumbnail, sq ft, part count |
| Drawing Layout | 3/10 | **Add scaled vector drawing zone** |
| Edge Representation | 1/7 | **Add visual edge differentiation** |
| Cutout Representation | 1/7 | **Add scaled cutout overlay** |
| Hole Representation | 1/5 | **Add scaled hole circles** |
| Splash Representation | 1/5 | **Add splash bands** |
| Seam Indicators | 0/3 | Add seam line between parts |
| Variant Handling | 3/6 | Add mirror geometry flip |
| Qty / Units | 3/4 | OK — minor gaps |
| Page Layout | 2/6 | Add drawing/notes column split, title block |
| Fabrication Notes | 2/5 | Move to notes column, box critical notes |
| Summary | 6/9 | Add part type counts, edge LF |

**TOTAL: 34 / 92 elements at MATCH (37%) → Phase 4 target: 65 / 92 (71%)**

---

## Phase 4 Priority Order (by fabrication impact)

### TIER 1 — CRITICAL (fabricator cannot use drawing without these)
1. **Scaled vector part drawing** — part outline to scale in drawing zone
2. **Cutout overlays** — dashed rect at correct position in drawing
3. **Hole circles** — circle with Ø label at correct position
4. **Splash bands** — shaded band along correct edge
5. **Edge visual differentiation** — line style per edge type (polished=thick, raw=dashed)
6. **Dimension callout lines** — leader lines with L × D on drawing

### TIER 2 — HIGH (shop quality)
7. **Drawing zone / notes column split** — ~60/40 layout
8. **Edge legend** — explain line types
9. **Scale callout** — "Scale: ¾" = 1'-0"" or "NTS" if not to scale
10. **Sheet N of M** — in page header
11. **Seam line** — between parts

### TIER 3 — MEDIUM (completeness)
12. Assembly thumbnail on type sheet
13. Sq ft + piece count on type sheet
14. Mirror geometry flip for MIR assemblies
15. Part type breakdown on summary
16. Edge linear footage on summary
17. Cover: issued_by / sheet count

---

## Rejected Features (ADR-001)

| Feature | Reason |
|---|---|
| North arrow / orientation indicator | Not a countertop convention |
| Free-form annotation tools | Generic CAD — not fabrication domain |
| DXF import/export | No integration path for Phase 4 |
| Material waste estimate | Business logic undefined; defer to Phase 6 |
| Reveal dimension for undermount | Requires surveying real reveal specs; defer Phase 5 |
