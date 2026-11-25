---
trigger: model_decision
description: "Apply whenever running code-review on diffs/PRs, spec-review on docs/specs/, or design-review on architectural plans (prepare_code_review.py, peer_review.py)."
---

# AI Review Governance & Invariants

<rule name="ai-review-governance">
<description>
Enforces rigorous architectural peer reviews for specifications and designs alongside fast, single-agent, zero-repo-pollution code reviews before production gating.
</description>

<constraints>
- **Direct Single-Agent `code-review` & Zero Repo Pollution**:
  - Execute `code-review` directly inside the active agent using `prepare_code_review.py` (local diff, repo-config discovery, scoped read-only CLI linters, and distilled language conventions) without spawning subagents or external review engines.
  - Report `code-review` findings directly in chat (or Brain Artifacts when extensive); never write `review.md`, `review.json`, `.code-review/`, or `docs/adr/` files into target repositories.
- **Sandbox Isolation for Engine-Backed Spec & Design Reviews**:
  - Engine-backed `spec-review` and `design-review` passes (`scripts/peer_review.py`) execute in isolated repo sandboxes with verdict leak tripwires (`assert_no_verdict_leaks`).
- **Orthogonal Review Dimensions & Blocker Discipline**:
  - Reviews can isolate structural invariants (`inv`) from domain completeness (`dom`) via `--dimension`.
  - `P0`/`P1` issues block sign-off and require code/spec remediation or evidence-backed rebuttal; `P2` findings are advisory.
- **Review Mode Routing (`/boost` vs `peer_review.py` vs `/gemini-web-oracle`)**: Recommend native `/boost` for in-harness codebase-grounded multi-perspective reasoning, `spec-review`/`design-review` (`peer_review.py`) for isolated cross-engine audits, and `/gemini-web-oracle` for zero-tool Gemini Web / Google-Search grounding.
</constraints>

<instructions>
- When reviewing or critiquing design specifications in docs/specs/, consult skill `spec-review`.
- When reviewing architectural plans or implementation blueprints against governing specifications, consult skill `design-review`.
- When reviewing, critiquing, or scoring code changes before commit or merge, consult skill `code-review`.
</instructions>
</rule>
