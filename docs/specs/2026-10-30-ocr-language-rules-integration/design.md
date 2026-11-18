# Technical Design: Alibaba Open-Code-Review Language Rule Corpus & Glob Matcher Integration

- **Feature ID**: `2026-10-30-ocr-language-rules-integration`
- **Spec**: [spec.md](spec.md)
- **Decisions**: [decisions.md](decisions.md)

---

## 1. Component & Interface Design

### 1.1 `scripts/review/rules/` (Addresses: `REQ-048`)
- Directory structure:
  ```text
  scripts/review/rules/
  ├── LICENSE.apache-2.0.txt
  ├── system_rules.json
  └── rule_docs/
      ├── default.md
      ├── go.md
      ├── python.md
      ├── rust.md
      ├── java.md
      ├── ts_js_tsx_jsx.md
      └── ... (all 57 .md files from alibaba/open-code-review/internal/config/rules/rule_docs/)
  ```

### 1.2 `scripts/review/rule_matcher.py` (Addresses: `REQ-048`, `REQ-049`)
- **Pure-Python Standard Library Implementation**:
  - `OBJC_SNIFF_PREFIXES: Tuple[str, ...] = ("#import", "#include", "#pragma", "#if", "#define", "@import", "@interface", "@implementation", "@class", "@protocol", "//", "/*")`
  - `extract_diff_paths(target_content: str, target_path: Optional[str] = None) -> List[str]`:
    - Scans `target_content` for `+++ b/<path>` and `diff --git a/<old> b/<path>` headers (ignoring `/dev/null`), preserving first-seen order.
    - If no diff headers are present and `target_path` is provided (and its basename is not a generic temp name like `target.file` or `review_XXXXXX`), falls back to `[target_path]`.
  - `expand_braces(pattern: str) -> List[str]`:
    - Recursively expands `{a,b,c}` segments (e.g., `**/*.{ts,js}` -> `["**/*.ts", "**/*.js"]`, `**/*{mapper,dao}*.xml` -> `["**/*mapper*.xml", "**/*dao*.xml"]`).
  - `match_doublestar(pattern: str, path: str) -> bool`:
    - Normalizes separators to `/` and lowercases both `pattern` and `path`.
    - Converts glob pattern to a compiled `re.Pattern` where `/**/` matches zero or more directory segments (`(?:/|/.+/)`), leading `**/` matches optional directory prefix (`(?:.+/)?`), `*` matches `[^/]*`, and `?` matches `[^/]`.
  - `sniffs_as_objc(path: str, diff_text: str = "") -> bool`:
    - Returns `False` unless `path.lower().endswith(".m")`.
    - Extracts the first non-blank added/context line for `path` from `diff_text` (or reads the first non-blank line if `path` exists on disk) and checks `first_line.startswith(OBJC_SNIFF_PREFIXES)`.
  - `resolve_rules_for_paths(paths: List[str], diff_text: str = "", rules_dir: Optional[str] = None) -> List[Tuple[str, str]]`:
    - Loads `system_rules.json` preserving `path_rule_map` key order (`json.loads(..., object_pairs_hook=list)`).
    - For each path in `paths`, resolves the rule filename (`objc.md` if `sniffs_as_objc`, else first matching `path_rule_map` entry, else `default_rule`).
    - Deduplicates by `rule_filename` while preserving first-seen order and returns `[(rule_filename, rule_content), ...]`.
  - `build_language_rules_context(target_content: str, target_path: Optional[str] = None, max_chars: int = 60_000) -> str`:
    - Resolves `(rule_filename, rule_content)` pairs for extracted diff paths (falling back to `[("default.md", default_content)]` when no paths are extracted) and formats them inside `<language_review_rules>...</language_review_rules>` up to `max_chars`.

### 1.3 `scripts/review/prompts.py` (Addresses: `REQ-050`)
- Import `build_language_rules_context` from `review.rule_matcher` (with fallback to `scripts.review.rule_matcher`).
- In `build_review_prompt(..., mode="code")`:
  - Append the **Ground A / Ground B Self-Verification & Protected-Subject Guardrail**:
    - **Ground A (Diff Scope Invariant)**: Never flag code or symbols that do not appear in the subject file's diff.
    - **Ground B (No Literal Diff Contradiction)**: Before emitting any issue, verify that no line in the diff directly contradicts your claim (e.g., claiming a check or usage is missing when it is present in the diff).
    - **Protected High-Severity Categories**: Prioritize memory safety, concurrency/race conditions, linkage/declaration consistency, and behavioral/compatibility regressions as `P0`/`P1`.
  - Append `build_language_rules_context(target_content, target_path)` when non-empty.

---

## 2. Verification & Test Plan

- **Unit & Integration Test Suite (`tests/test_ocr_language_rules.py`)**:
  - Verify `AC-048-1`: All 58 `path_rule_map` globs and all 57 `rule_docs/*.md` files exist and load cleanly.
  - Verify `AC-049-1`–`AC-049-4`: Specificity precedence (`.github/workflows/ci.yml` vs `config.yml`), brace expansion (`**/*.{ts,js,tsx,jsx,mjs,cjs}`, `**/*{mapper,dao}*.xml`), root vs nested paths (`main.go` vs `a/b/main.go`), `.m` Objective-C vs MATLAB sniffing, and multi-file rule deduplication.
  - Verify `AC-050-1`–`AC-050-2`: `build_review_prompt(mode="code", ...)` injects `<language_review_rules>` and Ground A/B guardrails, whereas `mode="spec"` and `mode="design"` do not.
  - Run full regression suite: `rtk pytest tests/` and `rtk python3 scripts/spec_checker.py --workspace . --feature-id 2026-10-30-ocr-language-rules-integration`.
