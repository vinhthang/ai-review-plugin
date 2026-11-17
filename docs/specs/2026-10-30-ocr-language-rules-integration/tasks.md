# Tasks: Alibaba Open-Code-Review Language Rule Corpus & Glob Matcher Integration

## Phase 1: Rule Corpus Vendoring, Matcher Implementation & Prompt Integration

- [x] **Task 1 (`REQ-048`)**: Vendor `system_rules.json` and all 57 `rule_docs/*.md` files (with Apache-2.0 attribution) from `alibaba/open-code-review/internal/config/rules/` into `scripts/review/rules/`.
- [x] **Task 2 (`REQ-049`)**: Implement `scripts/review/rule_matcher.py` (`extract_diff_paths`, `expand_braces`, `match_doublestar`, `sniffs_as_objc`, `resolve_rules_for_paths`, and `build_language_rules_context`).
- [x] **Task 3 (`REQ-050`)**: Update `scripts/review/prompts.py` (`build_review_prompt` in `--mode code`) to inject `<language_review_rules>` and the Ground A / Ground B false-positive verification guardrail.
- [x] **Task 4 (`REQ-048`, `REQ-049`, `REQ-050`)**: Create `tests/test_ocr_language_rules.py` covering all acceptance criteria (`AC-048-1`, `AC-049-1`–`AC-049-4`, `AC-050-1`–`AC-050-2`) and run full `rtk pytest` and `spec_checker.py` verification.
