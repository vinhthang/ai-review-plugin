# AI Review Governance & Invariants

<rule name="ai-review-governance">
<description>
Enforces adversarial, multi-engine autonomous peer reviews across specifications, architecture plans, and code implementations before production gating.
</description>

<constraints>
- **Independent Sandbox Isolation**:
  - All review passes must execute in isolated repo sandboxes with verdict leak tripwires (`assert_no_verdict_leaks`).
  - Prior evaluation outcomes (`review.md`, `traceability_audit.json`, `SELF_REVIEW.md`, `architecture_review.md`, `REVERIFICATION_REPORT.md`) are excluded to avoid reviewer bias.
- **Orthogonal Review Dimensions**:
  - Review runs can isolate structural invariants (`inv`) from domain completeness (`dom`) via `--dimension`.
- **Zero Suppression & Blocker Discipline**:
  - P0/P1 issues block execution and require remediation or evidence-backed rebuttal before sign-off.
</constraints>

<instructions>
- When reviewing or critiquing design specifications in docs/specs/, consult skill `spec-review`.
- When reviewing architectural plans or implementation blueprints against governing specifications, consult skill `design-review`.
- When reviewing, critiquing, or scoring code changes before commit or merge, consult skill `code-review`.
</instructions>
</rule>
