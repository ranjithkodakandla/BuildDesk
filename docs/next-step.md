# Next Step

> Auto-updated after each milestone. Always read this before starting a new session.

---

## Current State

| Field              | Value                                  |
|--------------------|----------------------------------------|
| Last completed phase | Phase 7 — Asynchronous Package Workflow & Artifact Storage |
| Git branch         | `feat/phase-7-async-packages` (to be committed) |
| Test baseline      | 54/54 backend, 13/13 frontend |
| Migration state    | Up to date |

---

## Immediate Next Milestone

**Phase 8 — Bulk-Unit Creation UI & UX Hardening**

Goal: Address the primary usability gap discovered in the Pilot Validation (Phase 6). Allow users to quickly generate hundreds of units based on patterns (e.g. Floors 1-5, Units 01-12) instead of single-record entry.

Priority tasks:
1. **Bulk Generation API** — Create a `POST /projects/{id}/units/bulk` endpoint that accepts floor ranges, unit numbering patterns, and a Unit Type mapping, and generates the units efficiently.
2. **Frontend UI** — Build a "Generate Units" modal in `HierarchyPanel.tsx` that provides a spreadsheet-like or pattern-based interface for mass unit creation.
3. **Assembly Duplication** — Add "Duplicate" action to `AssembliesPanel.tsx` to easily clone a base Kitchen assembly to a MIRROR variant.

Domain test: Can a user instantiate a 150-unit building with 4 unit types in under 60 seconds of interaction?

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
