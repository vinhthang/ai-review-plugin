---
trigger: always_on
description: "Enforces 5-Document Architecture precedence, ADR decisions.md, and requirement ID traceability when planning and authoring specifications."
---

<rule name="spec-standard">
<description>
Enforces precedence order, requirement ID traceability, and authority boundaries when authoring specifications in docs/. For detailed templates and directory layouts, see skill spec-standard.
</description>

<scope>
- **Mandatory (5-Document Architecture)**: Multi-file features, architectural refactors, public API changes, or whenever `/plan` is invoked. Touching >=2 code files, adding/modifying CLI switches/arguments, altering public APIs, or changing data schemas strictly invalidates the fast path.
- **Exempt (Fast Path)**: Single-file typo fixes, 1-line bug fixes with regression tests, or minor config adjustments touching <= 1 file remain exempt.
</scope>

<constraints>
- **The 5-Document Architecture**:
  1. `spec.md`: What must be true (Living, versioned, human-approved).
  2. `decisions.md`: What has been explicitly decided (ADR rationale, append-only).
  3. `design.md`: How we intend to build it (Revisable architecture blueprint).
  4. `tasks.md`: What remains to be done (Execution checklist).
  5. `verification.md`: Verbatim evidence that it works (Append-only per run).
- **User Execution Constraints != Phase Skips**: Direct instructions describing execution parameters ("update the code but do not recompile", "run in background") specify negative or procedural constraints, NEVER an authorization to bypass Phase 1 (Planning & Specification).
- **Planning Phase Integration (`/plan`)**:
  - When `/grill-me` precedes `/plan`, it establishes `spec.md` and `decisions.md` (the ADR).
  - When `/plan` is invoked, author `design.md` and `tasks.md`. If invoked without `/grill-me`, scaffold `spec.md`, `decisions.md`, and `design.md` together under `docs/specs/<feature-id>/`.
  - The ephemeral plan artifact in the brain directory is an operational dashboard derived from in-repo documents. Approving the plan confirms human sign-off on underlying `spec.md`, `decisions.md`, and `design.md`.
  - **Slash Command Precedence**: When `/plan` is invoked, the repository's 5-Document Architecture (`docs/specs/<feature-id>/` and `docs/specs/INDEX.md`) takes strict precedence over any built-in or default IDE plan template (e.g. generic `<PLAN>` artifact guidelines). The Primary Agent MUST author the in-repo specification files first before or concurrently with deriving the ephemeral `implementation_plan.md` artifact dashboard.
  - **No Artifact Chat Redundancy**: Do not dump or re-summarize implementation plan markdown into the chat response; link to the artifact and present key decisions and next steps per `RULE[reasoning-quality]`.
- **Precedence Order & Invalidation**:
  - `spec.md` > `decisions.md` > `design.md` > `tasks.md`. `verification.md` can invalidate any document, but may never redefine normative requirements in `spec.md`.
  - When `verification.md` records an assertion break against a `REQ-xxx`, execution immediately halts and routes to Root Cause Diagnosis (Dalio Step 3).
- **Requirement ID Traceability**: Every requirement MUST have a stable ID (e.g. `REQ-001`) with testable acceptance criteria in `spec.md`. That ID must be cited in `decisions.md`, `design.md`, `tasks.md`, and `verification.md`. Evidence without an ID is unaccounted activity.
- **Conflict Resolution**: When documents contradict, STOP work and apply precedence. Propose design adjustments; never silently weaken `spec.md` to match an implementation or test.
- **Review Input Boundary**: Peer reviews evaluate normative contracts (`spec.md`, `design.md`, `decisions.md`). Operational execution checklists (`tasks.md`, `verification.md`) are excluded from peer review inputs.
- **IDE Approval Conduit**: Ephemeral `implementation_plan.md` in the artifact directory is an operational dashboard derived strictly from underlying spec documents. Approving the plan confirms human sign-off on underlying `spec.md`, `decisions.md`, and `design.md`.
</constraints>

<instructions>
- Organize feature workstreams under `docs/specs/<feature-id>/` and register feature IDs in `docs/specs/INDEX.md`.
- Follow the 5-Document Architecture templates and scaling switches in `skill: spec-standard`.
</instructions>
</rule>
