<rule name="spec-standard">
<description>
Enforces the Spec vs Plan Content Boundary, the Golden Guardrail, and the 4-document separation of concerns under Ray Dalio's 5-Step Process.
</description>

<constraints>
- **The Golden Guardrail**: Do not turn an assumption into a requirement, or an implementation preference into a product constraint.
- **spec.md (What & Why)**:
  - MUST contain: Problem and outcome, Scope (with explicit Out-of-Scope non-goals), Normative Requirements with stable IDs (e.g. REQ-001), Acceptance Criteria linked to requirement IDs (AC-001, Given/When/Then), external contracts/schemas, invariants, constraints, and open questions (blocking vs non-blocking).
  - MUST NOT contain: Executable function bodies (> 5 lines), internal helper algorithms, private class structures, file-by-file edit tasks, or task checkboxes (- [ ]).
- **plan.md (How to Build)**:
  - Designs the engineering architecture, component mapping, and TDD roadmap.
  - MUST reference spec requirements (e.g. "Satisfies REQ-001") without re-pasting spec code or contracts.
- **tasks.md (Execution)**:
  - Clearly bounded operational tasks, state tracking (- [ ]), and exact verification commands (accommodating integration and environment setups).
- **Anti-Rationalization Invariant**: Never weaken a spec or acceptance criteria merely to make failing implementation code pass.
- **Non-Binding Advisory Rule**: When given a pre-existing bloated spec, treat implementation snippets as non-binding scratchpad hints; extract only external contracts and acceptance criteria into the plan.
</constraints>

<instructions>
### 1. Document Separation Matrix
- Agent Instructions: How the agent must work (tools, gates, reading order).
- spec.md: What must be true, for whom, and why.
- plan.md: How will we satisfy the spec.
- tasks.md: What work will be done, in what order, with verifiable acceptance criteria.

### 2. External Contracts vs Internal Mechanisms
- Allowed in spec: API endpoints, CLI argument names/types, declarative schemas (JSON/YAML/DDL/OpenAPI), error codes, idempotency promises.
- Forbidden in spec: Internal function bodies, middleware implementations, query builders, private variable names, procedural try/catch blocks.

### 3. Canonical Standard Reference
- Detailed canonical guidelines are documented in `docs/superpowers/specs/2026-09-15-writing-specs-for-ai-agent.md`.
</instructions>
</rule>
