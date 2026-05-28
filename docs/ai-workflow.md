# BuildDesk AI Workflow Rules

All AI coding tools working on BuildDesk must follow these rules.

Applies to:

* Codex
* Cursor
* Antigravity
* Claude
* Any future coding assistant

## Context Rules

Before making changes, always read:

* docs/vision.md
* docs/architecture.md
* docs/mvp.md
* docs/current-state.md
* docs/ai-workflow.md

Understand product goals before writing code.

## Documentation Update Rule

Whenever code changes are made:

Update documentation if applicable.

Examples:

New feature:
→ update docs/current-state.md

Architecture decision:
→ update docs/architecture.md

Scope change:
→ update docs/mvp.md

Business direction change:
→ update docs/vision.md

## Current State Tracking

Keep docs/current-state.md continuously updated.

Track:

Completed work
Work in progress
Next priorities

## Development Rules

Prefer:

* clean architecture
* modular code
* multi-tenant ready design
* backend-first approach
* future SaaS compatibility

Avoid:

* hardcoded Canyon-specific logic
* tight StoneDesk coupling
* premature optimization

## Commit Guidance

After meaningful milestones:

suggest git commit message.
