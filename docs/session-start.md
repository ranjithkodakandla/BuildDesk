# BuildDesk — Mandatory Session Start Protocol
> **Every development session — human or AI — must complete this checklist before writing a single line of code.**
> This prevents context loss, roadmap drift, and domain violations across machine switches and conversation resets.

---

## Step 1 — Read These Three Documents (in order)

```
docs/domain-guardrail.md    ← ADR-001. The law. No exceptions.
docs/current-state.md       ← What is done. What is passing. What is blocked.
docs/architecture.md        ← System design, layer responsibilities, hierarchy.
```

Do not skip. Do not skim. These are the source of truth.

---

## Step 2 — Read the Active Next Step

```
docs/next-step.md           ← Current phase, active branch, immediate next milestone, blockers.
```

This file is updated after every committed milestone. It tells you exactly where to continue.

---

## Step 3 — Verify Repo State

Run these commands before touching any code:

```bash
# Confirm you are on the correct branch
git branch

# Confirm HEAD matches the expected milestone commit
git log --oneline -5

# Confirm all migrations are applied
cd backend && alembic current

# Confirm tests are green
cd backend && python -m pytest tests/ -q
```

Expected baseline before Phase 3:
- Branch: `main` (or active feature branch from `next-step.md`)
- HEAD: `c0c7e5d` (docs: ADR-001 guardrail) or later
- Alembic: `b2c3d4e5f6g7` (head — fabrication domain)
- Tests: 142 / 142 passing

---

## Step 4 — Apply the Domain Guardrail Test

Before proposing any task, ask:

> **Could this feature contribute toward generating a real fabrication package
> for a multifamily countertop project?**

- ✅ YES → proceed
- ❌ NO → do not implement. Log the rejection in `docs/domain-guardrail.md` rejection table.

Full checklist is in `docs/domain-guardrail.md` § Evaluation Checklist.

---

## Step 5 — Confirm Active Milestone Scope

State the exact milestone being worked on.  
If it does not match `docs/next-step.md`, stop and reconcile before proceeding.

Use the template in `docs/milestone-template.md` to scope the work.

---

## Session Start Summary Card

```
┌─────────────────────────────────────────────────────────────────┐
│  BuildDesk Session Start Checklist                              │
├─────────────────────────────────────────────────────────────────┤
│  □  Read docs/domain-guardrail.md                               │
│  □  Read docs/current-state.md                                  │
│  □  Read docs/architecture.md                                   │
│  □  Read docs/next-step.md                                      │
│  □  git log --oneline -5  (verify HEAD)                         │
│  □  alembic current       (verify migrations)                   │
│  □  pytest -q             (verify green baseline)               │
│  □  Apply domain guardrail test to proposed work                │
│  □  Confirm milestone scope matches next-step.md                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why This Exists

BuildDesk has experienced:
- **Machine switching** — development moved between machines, losing active context
- **AI session resets** — new conversation windows lose prior milestone state
- **Roadmap drift** — features implemented that don't serve the fabrication workflow

This protocol exists to make those failure modes structurally impossible.
The documents are the memory. The checklist is the lock.
