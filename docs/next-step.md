# Next Step

> Auto-updated after each milestone. Always read this before starting a new session.

---

## Current State

| Field              | Value                                  |
|--------------------|----------------------------------------|
| Last completed phase | Phase 10 — Export Engine Enhancements (Round-Trip Workflow) |
| Git branch         | `feat/phase-10-export-engine` |
| Test baseline      | Passing backend, frontend compiled |
| Migration state    | Up to date |

---

## Immediate Next Milestone

**Phase 11 — Export Engine PDF Overhaul (Dimension Callouts, Cover Page, TOC)**

The system is ready to proceed to Phase 11.

### Next Execution Target: Phase 11 — Export Engine PDF Overhaul

With the operational exports (CSV/XLSX) complete for schedules and fabrication counts, the focus must shift to upgrading the visual layout and fidelity of the PDF artifact generation.

**Key Objectives for Phase 11:**
1. **Dimension Callouts:** Implement automated dimensional annotations on SVG vectors so that shop floor workers can read measurements directly from the diagrams without manual scaling.
2. **Cover Page Generation:** Add a professional cover page to the PDF package, including project metadata, total unit counts, revision history, and standard fabrication notes.
3. **Table of Contents:** Include an index page mapping unit types to their corresponding package pages for easier navigation in large (100+ page) printouts.
4. **Drawing Template Overhaul:** Improve the border, title block, and layout of individual drawing pages to look like standard architectural/fabrication shop drawings.

**Required Verification:**
- Generate the pilot project package and visually compare the newly generated PDF against real-world examples (like those from Canyon) to ensure dimensioning and title blocks are acceptable.

---

## Pending Blockers

- None currently blocking Phase 11.
