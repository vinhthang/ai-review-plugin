<rule name="spec-standard">
<description>
Enforces the 5-Document Architecture for strict lifecycle separation, precedence order, and requirement ID tracking.
</description>

<constraints>
- **The 5-Document Architecture**:
  1. `spec.md`: What must be true (Living, versioned, human-approved).
  2. `decisions.md`: What has been explicitly decided (Append-only, superseded but never edited).
  3. `design.md`: How we intend to build it (Revisable architecture blueprint).
  4. `tasks.md`: What remains to be done (Volatile, execution checkboxes).
  5. `verification.md`: Evidence that it works (Append-only per run, verbatim tool output).
- **Precedence Order**: `spec.md` > `decisions.md` > `design.md` > `tasks.md`. `verification.md` can invalidate any document, but may never redefine the spec.
- **Scaling Switches**: The base configuration is `spec.md` + `design.md` + `tasks.md`. Only add `decisions.md` for rationale that must outlive the decision. Only add `verification.md` when correctness must be demonstrated with reproducible evidence.
- **Requirement IDs (The Spine)**: Every normative requirement MUST have a stable ID (e.g., REQ-001) in `spec.md`. This ID must be threaded through all 5 documents to maintain traceability.
- **Conflict Protocol**: When documents disagree, STOP the affected work. Name the conflict and apply the precedence order. Never silently reconcile a mismatch by editing whichever file is convenient.
</constraints>

<instructions>
### 1. Document Authority
When verifying an implementation, the source of truth is always `spec.md`. If a test fails because the `design.md` contradicts `spec.md`, the design is wrong. Propose a change to the design, do not weaken the spec to make tests pass.

### 2. Traceability Enforcement
When updating `tasks.md` or writing to `verification.md`, you must explicitly cite the requirement ID (e.g., `Requirements: REQ-007`). An ID with no evidence is unverified work. Evidence with no ID is unaccounted activity.
</instructions>
</rule>
