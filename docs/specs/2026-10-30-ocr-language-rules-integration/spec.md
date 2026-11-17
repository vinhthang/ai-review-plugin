# Specification: Alibaba Open-Code-Review Language Rule Corpus & Glob Matcher Integration

- **Feature ID**: `2026-10-30-ocr-language-rules-integration`
- **Status**: `Approved`
- **Version**: `1.0.0`
- **Date**: `2026-10-30`
- **Authors**: `Primary Agent`

## 1. Context & Motivation

1. **Generic Code-Review Prompt in `scripts/review/prompts.py`**:
   - Currently, `build_review_prompt(..., mode="code")` in `scripts/review/prompts.py` (lines 217–227) provides only a generic 1-line instruction (`"Focus on code-level issues, logic, and correctness."`) plus the Markdown documentation guardrail.
   - Without language-specific positive defect checklists and negative false-positive suppressors, reviewer engines (`workbuddy`, `argon`, `codex`) either miss subtle runtime semantics (e.g., Go typed-nil interface traps, Rust synchronous lock guards held across `.await`, Python mutable defaults and blocking I/O in `async def`) or emit false positives on modern language semantics (e.g., flagging Go 1.22+ range-loop variable capture or Go 1.23+ unreferenced timer GC recovery).
2. **Alibaba `open-code-review` (`internal/config/rules/`) Rule Corpus & Glob Matcher**:
   - `alibaba/open-code-review` (Apache-2.0) ships `internal/config/rules/system_rules.json` (58 specificity-ordered glob patterns including `**/*.gradle.kts` + `default.md` fallback) and 57 curated language/format checklists in `internal/config/rules/rule_docs/*.md`, paired with brace-expanding doublestar glob matching (`system_rules.go`), `.m` Objective-C vs. MATLAB content sniffing (`sniffer.go`), rule deduplication (`rulegroup.go`), and a 2-ground false-positive filter (`review_filter_task_user.md`).
3. **Goal**:
   - Vendor the `alibaba/open-code-review` language rule corpus (`system_rules.json` + 57 `rule_docs/*.md` files) into `ai-review-plugin` under `scripts/review/rules/`, implement the deterministic Python glob/sniff matcher in `scripts/review/rule_matcher.py`, and inject deduplicated `<language_review_rules>` and Ground A/B false-positive verification guardrails into `scripts/review/prompts.py` during `--mode code` reviews.

---

## 2. Architecture & System Model

```
+------------------------+     +-----------------------------------+     +-----------------------------------+
|  Unified Diff / Target | --> |   scripts/review/rule_matcher.py  | --> |    scripts/review/prompts.py      |
|  (target_content,      |     | 1. extract_diff_paths()           |     | Injects <language_review_rules>   |
|   target_path)         |     | 2. expand_braces() + doublestar   |     | + Ground A/B Verification         |
+------------------------+     | 3. sniffs_as_objc() (.m files)    |     | Guardrail in --mode code          |
                               | 4. Deduplicate matched rule_docs  |     +-----------------------------------+
                               +-----------------------------------+
                                                 ^
                                                 |
                               +-----------------------------------+
                               |    scripts/review/rules/          |
                               | - system_rules.json (58 globs)    |
                               | - rule_docs/*.md (57 checklists)  |
                               +-----------------------------------+
```

### Scope Exclusions & Non-Goals
- **No Test File Filtering**: Unlike `alibaba/open-code-review`'s `default_exclude_patterns.json` (which drops `*_test.go` and `__tests__`), `ai-review-plugin` MUST NOT exclude test files from review, preserving compliance with `RULE[tdd.md]`.
- **No Spec/Design Prompt Alteration**: `--mode spec` and `--mode design` prompts remain unchanged.

---

## 3. Component & Interface Contracts

### 3.1 `scripts/review/rules/` (Corpus Package)
- `scripts/review/rules/system_rules.json`: JSON object containing `"default_rule": "default.md"` and `"path_rule_map"` preserving key declaration order.
- `scripts/review/rules/rule_docs/*.md`: 57 Markdown rule files (`arkts.md`, `astro.md`, `bicep.md`, `build_gradle.md`, `c.md`, `capnp.md`, `cargo_toml.md`, `composer_json.md`, `cpp.md`, `default.md`, `elm.md`, `freemarker.md`, `fsharp.md`, `github_config.md`, `github_workflows.md`, `go.md`, `graphql.md`, `handlebars_mustache.md`, `haskell.md`, `java.md`, `jinja.md`, `json.md`, `jsonnet.md`, `julia.md`, `kotlin.md`, `mapper_dao_xml.md`, `matlab.md`, `nim.md`, `nix.md`, `nushell.md`, `objc.md`, `ocaml.md`, `package_json.md`, `php.md`, `po.md`, `pom_xml.md`, `pot.md`, `powershell.md`, `prisma.md`, `properties.md`, `protobuf.md`, `pug.md`, `python.md`, `r.md`, `rego.md`, `rust.md`, `shader.md`, `solidity.md`, `swift.md`, `terraform.md`, `thrift.md`, `ts_js_tsx_jsx.md`, `verilog.md`, `vhdl.md`, `vyper.md`, `yaml.md`, `zig.md`).

### 3.2 `scripts/review/rule_matcher.py`
- `extract_diff_paths(target_content: str, target_path: Optional[str] = None) -> List[str]`
- `expand_braces(pattern: str) -> List[str]`
- `match_doublestar(pattern: str, path: str) -> bool`
- `sniffs_as_objc(path: str, diff_text: str = "") -> bool`
- `resolve_rules_for_paths(paths: List[str], diff_text: str = "", rules_dir: Optional[str] = None) -> List[Tuple[str, str]]`
- `build_language_rules_context(target_content: str, target_path: Optional[str] = None, max_chars: int = 60_000) -> str`

### 3.3 `scripts/review/prompts.py`
- In `build_review_prompt(..., mode="code")`, call `build_language_rules_context(target_content, target_path)` and append `<language_review_rules>...</language_review_rules>` and the Ground A/B self-verification guardrail.

---

## 4. Error Handling & Failure Modes

- **Missing or Unreadable Rule File**: If `system_rules.json` or a referenced `.md` file is missing or unreadable at runtime, `rule_matcher.py` logs a warning to `sys.stderr` and degrades gracefully to returning an empty string without crashing `peer_review.py`.
- **Oversized Rule Context**: If a changeset touches dozens of distinct languages, `build_language_rules_context()` enforces `max_chars` (default `60_000` characters) so the prompt never exceeds engine context limits.

---

## 5. Normative Requirements & Verification Criteria

### `REQ-048`: Vendored Language Rule Corpus (`scripts/review/rules/`)
- **Statement**: `ai-review-plugin` MUST vendor `alibaba/open-code-review`'s `system_rules.json` and all 57 language/format checklists under `scripts/review/rules/system_rules.json` and `scripts/review/rules/rule_docs/*.md` with Apache-2.0 attribution.
- **Acceptance Criteria**:
  - `AC-048-1`: `scripts/review/rules/system_rules.json` parses as valid JSON containing `"default_rule": "default.md"` and all 58 `"path_rule_map"` entries, and all 57 `.md` files in `scripts/review/rules/rule_docs/` exist and are non-empty.

### `REQ-049`: Deterministic Glob Matcher, `.m` Content Sniffer & Diff Path Extractor (`scripts/review/rule_matcher.py`)
- **Statement**: `scripts/review/rule_matcher.py` MUST extract modified file paths from unified diffs (or single target files), match paths case-insensitively against `system_rules.json` in declaration order supporting `**` recursive globs and `{a,b}` brace expansion, disambiguate `.m` files via Objective-C first-line sniffing, and deduplicate matched rule bodies.
- **Acceptance Criteria**:
  - `AC-049-1`: Specificity ordering is preserved: `.github/workflows/ci.yml` resolves `github_workflows.md` (not `yaml.md`), and `src/dao/UserMapper.xml` resolves `mapper_dao_xml.md`.
  - `AC-049-2`: Brace expansion and `**/` globs match both root-level (`main.go` -> `go.md`, `index.tsx` -> `ts_js_tsx_jsx.md`) and nested (`internal/agent/agent.go` -> `go.md`, `scripts/review/prompts.py` -> `python.md`) paths case-insensitively.
  - `AC-049-3`: `.m` files sniff as `objc.md` when their first non-blank line or added diff line starts with an Objective-C prefix (`#import`, `#include`, `#pragma`, `#if`, `#define`, `@import`, `@interface`, `@implementation`, `@class`, `@protocol`, `//`, `/*`), and `matlab.md` otherwise.
  - `AC-049-4`: When multiple files in a diff match the same rule (e.g., 5 `.go` files and 2 `.py` files), `resolve_rules_for_paths()` returns each matched rule body (`go.md`, `python.md`) exactly once in deterministic first-seen order.

### `REQ-050`: Code-Review Prompt Injection & Ground A/B Verification Guardrail (`scripts/review/prompts.py`)
- **Statement**: `build_review_prompt()` in `scripts/review/prompts.py` MUST inject the resolved `<language_review_rules>` block and the Ground A / Ground B false-positive verification guardrail when `mode == "code"`, while leaving `mode == "spec"` and `mode == "design"` unchanged.
- **Acceptance Criteria**:
  - `AC-050-1`: Calling `build_review_prompt(mode="code", ...)` on a diff containing `.go` and `.py` modifications produces a prompt containing `<language_review_rules>`, the deduplicated contents of `go.md` and `python.md`, and the Ground A / Ground B verification instructions.
  - `AC-050-2`: Calling `build_review_prompt(mode="spec", ...)` or `build_review_prompt(mode="design", ...)` does not inject `<language_review_rules>`.
