# Feature Registry & Requirement Index

This catalog indexes all feature specifications, requirement ID ranges, and architectural decision records.

| Feature ID | Title | Status | REQ Range | Key Decisions | Spec Path |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `2026-09-13-workbuddy-review-engine` | WorkBuddy Review Engine Integration | Completed | `REQ-001`–`REQ-005` | WorkBuddy headless bundle, CLI adapters | [`2026-09-13-workbuddy-review-engine-specification.md`](./2026-09-13-workbuddy-review-engine-specification.md) |
| `2026-09-15-5file-architecture` | 5-File Architecture & Precedence | Completed | `REQ-006`–`REQ-010` | 5 distinct lifecycles, Precedence Order | [`2026-09-15-writing-specs-for-ai-agent.md`](./2026-09-15-writing-specs-for-ai-agent.md) |
| `2026-09-16-versioned-reviews` | Feature-Scoped Docs & Versioned Reviews | Completed | `REQ-011`–`REQ-020` | Stateless `--prior-review`, `INDEX.md`, package layout | [`2026-09-16-versioned-reviews/spec.md`](./2026-09-16-versioned-reviews/spec.md) |
| `2026-09-16-modular-review-flows` | Modular Review Architecture Refactor | Completed | `REQ-021`–`REQ-025` | Numbered State Transitions (Audit, Remediation, Governance), Stateless Rebuttals | [`2026-09-16-modular-review-flows/spec.md`](./2026-09-16-modular-review-flows/spec.md) |
| `2026-10-06-code-review-rebuttal-and-docs-guardrails` | Code-Review Rebuttal Protocol & Docs Guardrails | Completed | `REQ-026`–`REQ-030` | Docs guardrail in audit prompt, stateless rebuttal for code-review, modular lifecycle alignment | [`docs/specs/2026-10-06-code-review-rebuttal-and-docs-guardrails/spec.md`](./2026-10-06-code-review-rebuttal-and-docs-guardrails/spec.md) |
| `2026-10-09-spec-gate-enforcement` | Mechanical Spec-Gate & Traceability Enforcement | Approved | `REQ-031`–`REQ-035` | Inter-plugin hook gate, AST traceability in CI | [`docs/specs/2026-10-09-spec-gate-enforcement/spec.md`](./2026-10-09-spec-gate-enforcement/spec.md) |
| `2026-10-14-argon-web-reviewer` | Argon Web Reviewer & Pluggable Engine Architecture | Completed | `REQ-036`–`REQ-040` | Pluggable Engine Registry, Edge AppleScript runner, Hybrid JSON/Markdown parser | [`docs/specs/2026-10-14-argon-web-reviewer/spec.md`](./2026-10-14-argon-web-reviewer/spec.md) |
| `2026-10-19-simplification-and-deduplication` | Codebase Simplification, Deduplication & Sub-500-Line Modularization | Approved | `REQ-041`–`REQ-044` | Single-source spec-standard rule, sub-500-line split (`prompts.py`, `cdp_client.py`), shared issue normalization | [`docs/specs/2026-10-19-simplification-and-deduplication/spec.md`](./2026-10-19-simplification-and-deduplication/spec.md) |
