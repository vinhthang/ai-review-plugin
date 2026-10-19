# Execution Tasks: Codebase Simplification, Deduplication & Modularization

- **Feature ID**: `2026-10-19-simplification-and-deduplication`
- **Status**: `Planning`

## Implementation Checklist

- [x] **Task 1: Deduplicate `rules/spec-standard.md`, sync `scripts/spec_checker.py`, and fix pipe splitting in `scripts/review/governance.py`** (`REQ-041`)
  - [x] Remove `ai-review-plugin/rules/spec-standard.md` (`AC-041-1`).
  - [x] Synchronize `scripts/spec_checker.py` from `spec-driven-plugin/scripts/spec_checker.py` with direct `parser.add_argument` declarations (`AC-041-1`).
  - [x] Update `update_index_catalog()` in `scripts/review/governance.py` to split columns via `re.split(r"(?<!\\)\|", ...)` (`AC-041-2`).
- [x] **Task 2: Extract `scripts/review/prompts.py` and modularize `scripts/review/audit.py` below 350 lines** (`REQ-042`)
  - [x] Create `scripts/review/prompts.py` with `build_review_prompt()` (`AC-042-1`).
  - [x] Extract `prepare_repo_sandbox()` and `execute_engine_process()` in `scripts/review/audit.py` (`AC-042-2`).
- [x] **Task 3: Extract `CDPClient` into `scripts/review/runners/cdp_client.py` below 360 lines** (`REQ-043`)
  - [x] Move `CDPClient` to `scripts/review/runners/cdp_client.py` and re-export it in `edge_applescript_runner.py` (`AC-043-1`, `AC-043-2`).
- [x] **Task 4: Centralize `extract_issue_description()` in `scripts/review/models.py` and run full verification** (`REQ-044`)
  - [x] Add `extract_issue_description()` in `scripts/review/models.py` and use it in `audit.py` and `argon.py` (`AC-044-1`).
  - [x] Run `pytest -v` and `python3 scripts/spec_checker.py --workspace . --allow-planning --json` and record verbatim outputs in `verification.md` (`AC-044-2`).
