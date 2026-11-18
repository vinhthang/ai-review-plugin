# Tasks: Harness² Blind Evaluator Sandbox Tripwire, INV/DOM Review & Surface Governance

## Phase 1: Blind Sandbox, INV/DOM Dimensions & Surface Compliance

- [x] **Task 1 (`REQ-045`)**: Add `VERDICT_LEAK_FILES`, `assert_no_verdict_leaks()`, and sandbox verdict stripping to `scripts/review/audit.py`.
- [x] **Task 2 (`REQ-046`)**: Add `--dimension {all,inv,dom}` CLI option to `scripts/review/audit.py` and `DIMENSION_FOCUS_PROMPTS` to `scripts/review/prompts.py`.
- [x] **Task 3 (`REQ-047`)**: Create `rules/AGENTS.md` with skill triggers (`spec-review`, `design-review`, `code-review`) and remove duplicate `skills/en-vi-book-translation-review`.
- [x] **Task 4 (`REQ-045`, `REQ-046`, `REQ-047`)**: Create `tests/test_harness2_review.py` and verify full test suite + `surface_validator.py` pass.
