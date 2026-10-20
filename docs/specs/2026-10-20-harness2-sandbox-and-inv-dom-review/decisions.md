# Architecture Decision Records: Sandbox Verdict Anti-Leak, Orthogonal INV/DOM Review & Surface Compliance

- **Feature ID**: `2026-10-20-harness2-sandbox-and-inv-dom-review`
- **Date**: `2026-10-20`

---

## `ADR-008`: Strip Verdict Artifacts in `prepare_repo_sandbox()` and Enforce `assert_no_verdict_leaks()`
- **Status**: Accepted
- **Addresses**: `REQ-045`
- **Context**:
  `prepare_repo_sandbox()` copied `review.md` and `traceability_audit.json` into `repo_copy`, risking reviewer bias from prior verdicts on disk.
- **Decision**:
  Exclude `VERDICT_LEAK_FILES` (`review.md`, `SELF_REVIEW.md`, `REVERIFICATION_REPORT.md`, `architecture_review.md`, `traceability_audit.json`) in `prepare_repo_sandbox()` and run `assert_no_verdict_leaks(repo_copy)` immediately after sandbox creation.
- **Consequences**:
  Guarantees blinded, independent review sandboxes.

---

## `ADR-009`: Orthogonal `INV` / `DOM` Review Dimensions & Plugin Surface Compliance
- **Status**: Accepted
- **Addresses**: `REQ-046`, `REQ-047`
- **Context**:
  Single-pass reviews conflate mechanical invariants (`INV`) with domain contracts (`DOM`), and `ai-review-plugin` lacked `rules/AGENTS.md` while carrying a duplicate `en-vi-book-translation-review` skill.
- **Decision**:
  Add `--dimension {all,inv,dom}` to `audit.py` and `build_review_prompt()` in `prompts.py`, create `rules/AGENTS.md` in `ai-review-plugin`, and remove the duplicate `skills/en-vi-book-translation-review` directory.
- **Consequences**:
  Enables targeted `INV`/`DOM` review passes and achieves 100% `surface_validator.py` compliance across all 5 installed plugins.
