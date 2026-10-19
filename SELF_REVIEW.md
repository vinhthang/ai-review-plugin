# Self-Review: `spec-driven-plugin` & `ai-review-plugin`

- **Date**: `2026-10-19`
- **Scope**:
  1. `spec-driven-plugin` (`/Users/thanghoang/github/spec-driven-plugin`)
  2. `ai-review-plugin` (`/Users/thanghoang/github/ai-review-plugin`)
- **Review Focus**: Code quality, simplicity, readability, maintainability, and edge-case correctness.

---

## 1. Executive Summary

Both plugins work as specified and have strong automated test suites (`34/34` passing in `spec-driven-plugin`, `136/136` passing in `ai-review-plugin`). Together, they form a two-layer governance system:
- **`spec-driven-plugin` (Mechanical Floor)**: Blocks code changes until a valid 4-document spec (`spec.md`, `decisions.md`, `design.md`, `tasks.md`) exists and is human-approved in `docs/specs/INDEX.md`.
- **`ai-review-plugin` (Intellectual Ceiling)**: Dispatches specs, designs, and diffs to external review engines (`workbuddy`, `codex`, `argon-web`) for adversarial critique.

However, looking at the two repositories critically through the lens of **simplicity and maintainability**, **5 structural issues** stand out:
1. **Cross-Repo Duplication**: `spec_checker.py` (489 lines) and `rules/spec-standard.md` live in both repos, creating maintenance drift and duplicate prompt rules.
2. **God-Functions & 500-Line File Limits**: `audit.py` (509 lines) and `edge_applescript_runner.py` (536 lines) exceed the 500-line AST gate limit, and `spec_checker.py` (489 lines) is 11 lines away. `audit._main()` is a single 412-line function.
3. **Three Different Markdown Table Parsers**: `INDEX.md` is parsed in three separate places using three different algorithms.
4. **Hardening Edge Cases in `spec-gate.py`**: Substring path matching on `.gemini/antigravity/brain` and partial-cell replacements on `INDEX.md` can be made both simpler and stricter.
5. **Library Methods Calling `sys.exit(2)`**: Adapter classes in `ai-review-plugin` call `sys.exit(2)` directly instead of raising exceptions, tangling CLI control flow with library logic.

---

## 2. How the Two Projects Fit Together (Mental Model)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Developer / Agent Workflow                      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼ Phase 1: Planning                                     ▼ Phase 2: Execution
┌─────────────────────────────────────┐               ┌─────────────────────────────────────┐
│         ai-review-plugin            │               │         spec-driven-plugin          │
│  Adversarial review of spec/design  │               │  PreToolUse hook (spec-gate.py)     │
│  via WorkBuddy / Codex / Argon Web  │               │  Blocks unapproved code mutations   │
└─────────────────┬───────────────────┘               └─────────────────┬───────────────────┘
                  │                                                     │
                  └──────────────────┬──────────────────────────────────┘
                                     ▼
                    ┌─────────────────────────────────┐
                    │     docs/specs/<feature-id>/    │
                    │  spec.md, decisions.md,         │
                    │  design.md, tasks.md,           │
                    │  verification.md + INDEX.md     │
                    └─────────────────────────────────┘
```

---

## 3. Findings & Simplification Recommendations

### Finding 1: Cross-Repository Duplication (`spec_checker.py` & `rules/spec-standard.md`)
- **Severity**: High (Maintainability & Context Bloat)
- **Locations**:
  - `spec-driven-plugin/scripts/spec_checker.py` (489 lines) vs. `ai-review-plugin/scripts/spec_checker.py` (489 lines)
  - `spec-driven-plugin/rules/spec-standard.md` vs. `ai-review-plugin/rules/spec-standard.md`
- **Problem**:
  1. Whenever `spec_checker.py` is updated in `spec-driven-plugin`, it must be manually copied to `ai-review-plugin`.
  2. Because both plugins are installed under `~/.gemini/config/plugins/`, the agent runtime loads **both** `rules/spec-standard.md` files into the system prompt on every turn. Worse, `ai-review-plugin/rules/spec-standard.md` is already slightly out of date compared to `spec-driven-plugin/rules/spec-standard.md` (missing the Phase 3 `<scope>` and approval boundary clauses).
- **How to Simplify**:
  - Make `spec-driven-plugin` the single source of truth for `spec_checker.py` and `rules/spec-standard.md`.
  - Remove `rules/spec-standard.md` from `ai-review-plugin` (or keep only review-specific rules in `ai-review-plugin`).

---

### Finding 2: Oversized Files & God-Functions (`> 500` Lines)
- **Severity**: High (Readability & Tooling Friction)
- **Locations**:
  - `ai-review-plugin/scripts/review/audit.py` (**509 lines**; `_main()` is **412 lines** from `L91` to `L502`)
  - `ai-review-plugin/scripts/review/runners/edge_applescript_runner.py` (**536 lines**)
  - `spec-driven-plugin/scripts/spec_checker.py` (**489 lines**; `verify_active_specification()` is **238 lines** from `L184` to `L421`)
- **Problem**:
  - The environment's `ast-gate.py` hook blocks `view_file` on any file exceeding 500 lines (`audit.py` and `edge_applescript_runner.py` already trigger this block).
  - In `audit.py`, `_main()` handles CLI parsing, flag validation, path containment, workspace `rsync`/`copytree` sandboxing, prompt building, subprocess execution with `SIGTERM`/`SIGKILL` timeouts, issue cleaning, and atomic file output in one uninterrupted 412-line block.
  - In `spec_checker.py`, `verify_active_specification()` mixes candidate path resolution (`L274-L337`) with status filtering and error aggregation.
- **How to Simplify**:
  1. **`audit.py` (509 -> ~220 lines)**:
     - Extract prompt construction (`L230-L315`) into `scripts/review/prompts.py`.
     - Extract subprocess execution with timeout cleanup (`L330-L410`) into `run_with_timeout(cmd, cwd, env, fout, ferr, timeout=1800)`.
     - Extract workspace copying (`L195-L228`) into `prepare_repo_sandbox(repo, work_dir)`.
  2. **`spec_checker.py` (489 -> ~360 lines)**:
     - Extract lines `274-337` into a small helper:
       ```python
       def resolve_package_dir(root: Path, specs_dir: Path, feat_id: str, spec_path_str: str) -> Tuple[Optional[Path], Optional[str]]:
           """Return (pkg_dir, path_error). Returns path_error if any candidate escapes root."""
       ```
     - This cuts `verify_active_specification()` in half and makes the status validation loop easy to read at a glance.
  3. **`edge_applescript_runner.py` (536 -> ~300 lines)**:
     - Move `CDPClient` (`L37-L233`) into `scripts/review/runners/cdp_client.py`.

---

### Finding 3: Three Separate `INDEX.md` Table Parsers
- **Severity**: Medium (Code Duplication & Bug Surface)
- **Locations**:
  1. `spec-driven-plugin/scripts/spec_checker.py` (`parse_specs_index()`, `L57-L110`)
  2. `spec-driven-plugin/scripts/spec-gate.py` (`is_unauthorized_status_promotion()`, `L118-L135`)
  3. `ai-review-plugin/scripts/review/governance.py` (`update_index_catalog()`, `L40-L45`)
- **Problem**:
  - `spec_checker.py` properly splits on unescaped pipes `re.split(r"(?<!\\)\|", trimmed[1:-1])` and enforces 6 columns.
  - `spec-gate.py` re-implements its own table row splitter (`L118-L135`) with `len(parts) >= 3`.
  - `governance.py` (`L41`) uses `row.split("|")[1:-1]`, which breaks if a table row contains an escaped pipe `\|`.
- **How to Simplify**:
  - Factor out `parse_specs_index_text(content: str) -> List[Dict[str, str]]` in `spec_checker.py`.
  - Call `parse_specs_index_text()` from both `parse_specs_index()` and `spec-gate.py`, deleting the custom loop in `spec-gate.py`.
  - Update `governance.py` to use `re.split(r"(?<!\\)\|", ...)`.

---

### Finding 4: Edge Cases in `spec-gate.py` Security Checks
- **Severity**: Medium (Security Hardening)
- **Locations**:
  - `spec-driven-plugin/scripts/spec-gate.py` (`is_allowed_runtime_artifact_path()`, `L57-L72`)
  - `spec-driven-plugin/scripts/spec-gate.py` (`is_unauthorized_status_promotion()`, `L75-L137`)
- **Problem**:
  1. **Substring Matching on Brain Path (`L60`)**:
     ```python
     if ".gemini/antigravity/brain" in target_str or ".gemini/antigravity/scratch" in target_str:
         return True
     ```
     Using substring matching (`in target_str`) means any external path containing those path segments (e.g., `/var/tmp/.gemini/antigravity/brain/file.py`) is allowed. Checking `target_path.resolve().is_relative_to(Path.home() / ".gemini" / "antigravity")` is both clearer and stricter.
  2. **Silent Fallback When `TargetContent` Does Not Match `disk_text` (`L97-L100`)**:
     In `is_unauthorized_status_promotion()`, `disk_text.replace(target_c, repl_c, 1)` returns `disk_text` unchanged if `target_c` does not match verbatim, and if `repl_c` is a single-cell edit (e.g. `"| Approved |"`), the fallback scan only checks lines with `len(parts) >= 3`.
- **How to Simplify & Harden**:
  - In `is_unauthorized_status_promotion()`, if `"TargetContent"` is provided and `target_c not in disk_text`, or if a partial table line (`len(parts) < 6`) in `ReplacementContent` contains an `EXECUTION_STATUSES` token (`approved`, `in-progress`, `active`), deny the edit immediately.

---

### Finding 5: Duplicated Issue Normalization & `sys.exit(2)` in Adapters (`ai-review-plugin`)
- **Severity**: Low–Medium (Code Cleanliness & Testability)
- **Locations**:
  - `ai-review-plugin/scripts/review/engines/argon.py` (`_normalize_issues()`, `L96-L129`)
  - `ai-review-plugin/scripts/review/audit.py` (`_main()`, `L439-L470`)
  - `ai-review-plugin/scripts/review/engines/workbuddy.py`, `codex.py`, `argon.py`, `engines/__init__.py`
- **Problem**:
  1. Both `argon.py` and `audit.py` contain nearly identical loops that inspect alternative dictionary keys (`details`, `message`, `summary`, `finding`, `title`, `comment`, `text`, `note`) to normalize LLM output into `{"severity": ..., "description": ...}`.
  2. Engine adapters call `sys.exit(2)` directly on errors instead of raising a dedicated `ReviewEngineError` exception. This forces unit tests to mock or catch `SystemExit` rather than testing normal Python exceptions.
- **How to Simplify**:
  - Move issue normalization into a single function `normalize_issues(raw_issues)` in `scripts/review/models.py` and call it once in `audit.py`.
  - Replace `print(..., file=sys.stderr); sys.exit(2)` inside engine classes with `raise ReviewEngineError(...)`, and catch `ReviewEngineError` in `audit.py:main()`.

---

## 4. Summary Scorecard

| Area | `spec-driven-plugin` | `ai-review-plugin` | Notes |
| :--- | :--- | :--- | :--- |
| **Correctness & Spec Compliance** | 9.5 / 10 | 9.0 / 10 | All normative requirements and edge cases covered by tests. |
| **Test Quality & Isolation** | 9.5 / 10 | 9.0 / 10 | Fast (`< 0.6s`), 100% isolated `tempfile` fixtures, 0 external network/repo dependencies. |
| **Simplicity & Readability** | 8.0 / 10 | 7.0 / 10 | `verify_active_specification()` (238 lines) and `audit._main()` (412 lines) should be broken into smaller helpers. |
| **DRY (No Duplication)** | 8.0 / 10 | 7.5 / 10 | `spec_checker.py`, `rules/spec-standard.md`, table parsing, and issue normalization are duplicated. |

---

## 5. Recommended Next Steps (In Priority Order)

1. **Deduplicate `rules/spec-standard.md` and `spec_checker.py`** so `spec-driven-plugin` is the single authoritative owner.
2. **Split `audit._main()` and `spec_checker.verify_active_specification()`** into focused 40–60 line helper functions so all files stay well under the 500-line AST gate threshold.
3. **Unify `INDEX.md` table parsing** into `spec_checker.parse_specs_index_text()` and reuse it in `spec-gate.py` and `governance.py`.
4. **Tighten `spec-gate.py`** runtime artifact path check to use `Path.is_relative_to()` instead of substring `in`, and reject partial-row status replacements on `INDEX.md`.
