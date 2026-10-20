# Specification: Sandbox Verdict Anti-Leak, Orthogonal INV/DOM Review Dimensions & Surface Compliance

- **Feature ID**: `2026-10-20-harness2-sandbox-and-inv-dom-review`
- **Status**: `Approved`
- **Version**: `1.0.0`
- **Date**: `2026-10-20`

## 1. Context & Motivation

1. **Evaluator Verdict Leakage in Sandbox (`scripts/review/audit.py`)**:
   - `prepare_repo_sandbox()` (lines 43–58) currently copies `review.md`, `SELF_REVIEW.md`, `REVERIFICATION_REPORT.md`, `architecture_review.md`, and `docs/specs/*/traceability_audit.json` into `repo_copy`. Modeled on `google-research/harness2/harness2/core/context.py` (`assert_no_leak_paths` and `assert_no_grader_verdicts`), independent review sandboxes must strip prior verdict artifacts before engine execution.
2. **Orthogonal `INV` vs. `DOM` Review Dimensions (`scripts/review/prompts.py` & `scripts/review/audit.py`)**:
   - Modeled on `google-research/harness2/harness2/core/prompts.py` (`_INV_TEMPLATE` vs. `_DOM_TEMPLATE`), `peer_review.py` (`audit.py` and `prompts.py`) should support `--dimension <all|inv|dom>` so callers can run focused **Invariant (`inv`)** reviews (process safety, CLI bounds, error handling, test falsifiability) or **Domain (`dom`)** reviews (specification completeness, state machine transitions, domain contracts).
3. **Plugin Surface Compliance (`rules/AGENTS.md` & Duplicate Skill Cleanup)**:
   - Running `surface_validator.py` on `ai-review-plugin` reported 4 untriggered skill errors (`code-review`, `design-review`, `spec-review`, and duplicate `en-vi-book-translation-review`).

---

## 2. Normative Requirements

### `REQ-045`: Sandbox Verdict Anti-Leak & Tripwire in `scripts/review/audit.py`
- **Statement**: `prepare_repo_sandbox()` in `scripts/review/audit.py` MUST exclude prior review and audit verdict files (`review.md`, `SELF_REVIEW.md`, `REVERIFICATION_REPORT.md`, `architecture_review.md`, `traceability_audit.json`) from `repo_copy` and verify via `assert_no_verdict_leaks(repo_copy)` that none remain in `repo_copy`.
- **Acceptance Criteria**:
  - `AC-045-1`: `VERDICT_LEAK_FILES` (`{"review.md", "SELF_REVIEW.md", "REVERIFICATION_REPORT.md", "architecture_review.md", "traceability_audit.json"}`) are excluded during `prepare_repo_sandbox()` and `assert_no_verdict_leaks(repo_copy)` raises `ValueError` if any leaked verdict file exists in `repo_copy`.

### `REQ-046`: Orthogonal `INV` and `DOM` Review Dimension Support (`scripts/review/prompts.py` & `scripts/review/audit.py`)
- **Statement**: `scripts/review/audit.py` and `scripts/review/prompts.py` MUST support `--dimension` (`"all"`, `"inv"`, `"dom"`, default `"all"`), injecting dimension-specific review instructions modeled on Harness² `INV` (invariant/mechanical) and `DOM` (domain/specification) templates.
- **Acceptance Criteria**:
  - `AC-046-1`: `audit.py` accepts `--dimension` with choices `["all", "inv", "dom"]` (default `"all"`) and passes `dimension=args.dimension` to `build_review_prompt()`.
  - `AC-046-2`: `build_review_prompt(..., dimension="inv"|"dom"|"all")` appends orthogonal `INV` or `DOM` focus directives when `dimension` is `"inv"` or `"dom"`.

### `REQ-047`: `ai-review-plugin` Surface Validation Compliance
- **Statement**: `ai-review-plugin` MUST include `rules/AGENTS.md` triggering its core review skills (`spec-review`, `design-review`, `code-review`), remove the duplicate `skills/en-vi-book-translation-review` directory, and pass `surface_validator.py` with 0 errors.
- **Acceptance Criteria**:
  - `AC-047-1`: `rtk python3 ~/.gemini/config/plugins/attention-guard/scripts/surface_validator.py --plugin-dir ~/.gemini/config/plugins/ai-review-plugin --json` exits `0` with `"valid": true` and `"errors": []`.
