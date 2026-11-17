# Verification Evidence: Alibaba Open-Code-Review Language Rule Corpus & Glob Matcher Integration

- **Feature ID**: `2026-10-30-ocr-language-rules-integration`
- **Specification**: [`spec.md`](spec.md)
- **Decisions**: [`decisions.md`](decisions.md)
- **Design**: [`design.md`](design.md)
- **Tasks**: [`tasks.md`](tasks.md)
- **Date**: `2026-10-30`

---

## 1. Summary of Verification Results

All automated test suites passing 100%:
- Dedicated Unit & Integration Tests: `tests/test_ocr_language_rules.py` (5/5 passed)
- Full Project Regression Suite: `tests/` (177/177 passed)
- Spec Package & Semantic Traceability: `scripts/spec_checker.py --workspace . --feature 2026-10-30-ocr-language-rules-integration --semantic` (passed: status=valid)

---

## 2. Requirement Traceability Matrix & Test Evidence

### `REQ-048`: Vendored Language Rule Corpus (`scripts/review/rules/`)

- **Acceptance Criteria**:
  - `AC-048-1`: `scripts/review/rules/system_rules.json` parses as valid JSON containing `"default_rule": "default.md"` and all `path_rule_map` entries, and all 57 `.md` files in `scripts/review/rules/rule_docs/` exist and are non-empty.
- **Test Target**: `tests/test_ocr_language_rules.py::TestOcrLanguageRules::test_req_048_vendored_rule_corpus`
- **Target Implementation**: `scripts/review/rules/system_rules.json`, `scripts/review/rules/rule_docs/*.md`, `scripts/review/rules/LICENSE.apache-2.0.txt`
- **Verbatim Evidence**:
```text
test_req_048_vendored_rule_corpus (tests.test_ocr_language_rules.TestOcrLanguageRules.test_req_048_vendored_rule_corpus)
AC-048-1: Verify system_rules.json and all 57 rule_docs/*.md files. ... ok
```

---

### `REQ-049`: Deterministic Glob Matcher, `.m` Content Sniffer & Diff Path Extractor (`scripts/review/rule_matcher.py`)

- **Acceptance Criteria**:
  - `AC-049-1`: Specificity ordering is preserved: `.github/workflows/ci.yml` resolves `github_workflows.md` (not `yaml.md`), and `src/dao/UserMapper.xml` resolves `mapper_dao_xml.md`.
  - `AC-049-2`: Brace expansion and `**/` globs match both root-level (`main.go` -> `go.md`, `index.tsx` -> `ts_js_tsx_jsx.md`) and nested (`internal/agent/agent.go` -> `go.md`, `scripts/review/prompts.py` -> `python.md`) paths case-insensitively.
  - `AC-049-3`: `.m` files sniff as `objc.md` when their first non-blank line or added diff line starts with an Objective-C prefix (`#import`, `#include`, `#pragma`, `#if`, `#define`, `@import`, `@interface`, `@implementation`, `@class`, `@protocol`, `//`, `/*`), and `matlab.md` otherwise.
  - `AC-049-4`: When multiple files in a diff match the same rule (e.g., 5 `.go` files and 2 `.py` files), `resolve_rules_for_paths()` returns each matched rule body (`go.md`, `python.md`) exactly once in deterministic first-seen order.
- **Test Targets**:
  - `tests/test_ocr_language_rules.py::TestOcrLanguageRules::test_req_049_specificity_and_brace_matching` (`AC-049-1`, `AC-049-2`)
  - `tests/test_ocr_language_rules.py::TestOcrLanguageRules::test_req_049_objc_vs_matlab_sniffing` (`AC-049-3`)
  - `tests/test_ocr_language_rules.py::TestOcrLanguageRules::test_req_049_deduplication_and_diff_extraction` (`AC-049-4`)
- **Target Implementation**: `scripts/review/rule_matcher.py` (`extract_diff_paths`, `expand_braces`, `match_doublestar`, `sniffs_as_objc`, `resolve_rules_for_paths`, `build_language_rules_context`)
- **Verbatim Evidence**:
```text
test_req_049_specificity_and_brace_matching (tests.test_ocr_language_rules.TestOcrLanguageRules.test_req_049_specificity_and_brace_matching)
AC-049-1 & AC-049-2: Specificity ordering and brace expansion matching. ... ok

test_req_049_objc_vs_matlab_sniffing (tests.test_ocr_language_rules.TestOcrLanguageRules.test_req_049_objc_vs_matlab_sniffing)
AC-049-3: Objective-C vs MATLAB .m content sniffing. ... ok

test_req_049_deduplication_and_diff_extraction (tests.test_ocr_language_rules.TestOcrLanguageRules.test_req_049_deduplication_and_diff_extraction)
AC-049-4: Diff path extraction and deduplication. ... ok
```

---

### `REQ-050`: Code-Review Prompt Injection & Ground A/B Verification Guardrail (`scripts/review/prompts.py`)

- **Acceptance Criteria**:
  - `AC-050-1`: Calling `build_review_prompt(mode="code", ...)` on a diff containing `.go` and `.py` modifications produces a prompt containing `<language_review_rules>`, the deduplicated contents of `go.md` and `python.md`, and the Ground A / Ground B verification instructions.
  - `AC-050-2`: Calling `build_review_prompt(mode="spec", ...)` or `build_review_prompt(mode="design", ...)` does not inject `<language_review_rules>`.
- **Test Target**: `tests/test_ocr_language_rules.py::TestOcrLanguageRules::test_req_050_code_mode_prompt_injection`
- **Target Implementation**: `scripts/review/prompts.py` (`build_review_prompt`)
- **Verbatim Evidence**:
```text
test_req_050_code_mode_prompt_injection (tests.test_ocr_language_rules.TestOcrLanguageRules.test_req_050_code_mode_prompt_injection)
AC-050-1 & AC-050-2: Injection into code-review prompt with Ground A/B guardrails. ... ok
```

---

## 3. Full Project Test Suite Verification

```text
$ cd /Users/thanghoang/.gemini/config/plugins/ai-review-plugin && rtk pytest tests/
Pytest: 177 passed
```

```text
$ cd /Users/thanghoang/.gemini/config/plugins/ai-review-plugin && rtk python3 scripts/spec_checker.py --workspace . --feature 2026-10-30-ocr-language-rules-integration --semantic
Specification verification passed: status=valid
Active features: 2026-10-30-ocr-language-rules-integration
```
