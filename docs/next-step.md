# Next Step

> Auto-updated after each milestone. Always read this before starting a new session.

---

## Current State

| Field              | Value                                  |
|--------------------|----------------------------------------|
| Last completed phase | Phase 8 — Bulk-Unit Creation UI & UX Hardening |
| Git branch         | `feat/phase-8-bulk-authoring` (to be committed) |
| Test baseline      | 62/62 backend, 18/18 frontend |
| Migration state    | Up to date |

---

## Immediate Next Milestone

**Phase 9 — Export Engine Enhancements**

The system is ready to proceed to Phase 9.

### Next Execution Target: Phase 9 — Export Engine Enhancements

With the application successfully supporting bulk authoring workflows and asynchronous package generation, the focus shifts back to the output artifacts themselves. The current exports (PDF and SVG) are functional but need refinement to match the visual fidelity and detail required by professional countertop fabricators.

**Key Objectives for Phase 9:**
1. **Dimension Callouts:** Implement automated dimensional annotations on SVG vectors so that shop floor workers can read measurements directly from the diagrams without manual scaling.
2. **Cover Page Generation:** Add a professional cover page to the PDF package, including project metadata, total unit counts, revision history, and standard fabrication notes.
3. **Table of Contents:** Include an index page mapping unit types to their corresponding package pages for easier navigation in large (100+ page) printouts.
4. **Drawing Template Overhaul:** Improve the border, title block, and layout of individual drawing pages to look like standard architectural/fabrication shop drawings.

**Required Verification:**
- Generate the pilot project package and visually compare the newly generated PDF against real-world examples (like those from Canyon) to ensure dimensioning and title blocks are acceptable.

---

## Pending Blockers

- None.

---

## Recommended Next Prompt

```
AUTONOMOUS IMPLEMENTATION MODE — Phase 8

Mandatory startup:
1. docs/session-start.md
2. docs/domain-guardrail.md
3. docs/current-state.md

PHASE 8 GOAL: Bulk-Unit Creation UI & UX Hardening.

Upgrade the authoring workflow for real-world scale:
1. Implement a bulk unit generation backend API.
2. Build a Bulk Units modal in the frontend.
3. Add assembly duplication.

Domain test: Creating 150 units should take less than 1 minute.
If NO → reject and document in ADR rejection table.

Branch: feat/phase-8-bulk-authoring
```
