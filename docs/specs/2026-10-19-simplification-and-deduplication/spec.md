# Specification: Codebase Simplification, Deduplication & Sub-500-Line Modularization

- **Feature ID**: `2026-10-19-simplification-and-deduplication`
- **Status**: `Planning`
- **Version**: `1.0.0`
- **Date**: `2026-10-19`

## 1. Problem Statement & Context

Following the self-review in [`SELF_REVIEW.md`](../../../SELF_REVIEW.md), four maintainability and structural issues remain in `ai-review-plugin`:
1. `rules/spec-standard.md` in `ai-review-plugin` duplicates `spec-driven-plugin/rules/spec-standard.md`, causing both rules to load simultaneously into the agent context and drift apart.
2. `scripts/review/audit.py` (509 lines; `_main()` is 412 lines) and `scripts/review/runners/edge_applescript_runner.py` (536 lines) exceed the 500-line AST gate threshold (`ast-gate.py`).
3. `scripts/review/governance.py` (`update_index_catalog()`) splits Markdown table rows using naive `row.split("|")[1:-1]`, which corrupts cells containing escaped pipes (`\|`).
4. Issue dictionary normalization (`details`/`message`/`summary` -> `description` and severity normalization) is duplicated between `scripts/review/audit.py` and `scripts/review/engines/argon.py`.

---

## 2. Normative Requirements

### `REQ-041`: Rule Deduplication, Shared Spec-Checker Sync & Escaped-Pipe Governance
- **Statement**: `ai-review-plugin` MUST remove its duplicate `rules/spec-standard.md` (deferring to `spec-driven-plugin/rules/spec-standard.md`), synchronize `scripts/spec_checker.py` (including direct `add_argument` declarations for `--feature`, `--allow-planning`, `--verify-evidence`, and `--semantic` alongside `--workspace`, `--json`, and `--quiet`), and use escaped-pipe regex splitting in `scripts/review/governance.py`.
- **Acceptance Criteria**:
  - `AC-041-1`: `ai-review-plugin/rules/spec-standard.md` is removed and `scripts/spec_checker.py` matches `spec-driven-plugin/scripts/spec_checker.py` with standard `parser.add_argument` declarations for `--feature`, `--allow-planning`, `--verify-evidence`, and `--semantic`.
  - `AC-041-2`: `update_index_catalog()` in `scripts/review/governance.py` splits table columns using `re.split(r"(?<!\\)\|", row.strip()[1:-1])` so escaped pipes (`\|`) inside cells are preserved.

### `REQ-042`: Sub-500-Line Modularization of `scripts/review/audit.py`
- **Statement**: `scripts/review/audit.py` MUST extract prompt construction into `scripts/review/prompts.py` and helper functions for sandbox preparation and process execution, reducing `audit.py` below 350 lines while preserving 100% backward compatibility.
- **Acceptance Criteria**:
  - `AC-042-1`: Prompt construction is extracted into `build_review_prompt()` in `scripts/review/prompts.py`.
  - `AC-042-2`: `scripts/review/audit.py` is under 350 lines, and `_main()` delegates sandbox setup, prompt building, and process execution to focused helpers.

### `REQ-043`: Sub-500-Line Modularization of `edge_applescript_runner.py`
- **Statement**: `scripts/review/runners/edge_applescript_runner.py` MUST extract `CDPClient` into `scripts/review/runners/cdp_client.py` (re-exporting `CDPClient` for backward compatibility), keeping both files under 360 lines.
- **Acceptance Criteria**:
  - `AC-043-1`: `CDPClient` resides in `scripts/review/runners/cdp_client.py` and is imported/re-exported by `edge_applescript_runner.py`.
  - `AC-043-2`: Both `cdp_client.py` and `edge_applescript_runner.py` are strictly under 360 lines (well below the 500-line AST gate limit).

### `REQ-044`: Centralized Issue Normalization in `scripts/review/models.py`
- **Statement**: `scripts/review/models.py` MUST provide a shared `extract_issue_description(item: Dict[str, Any]) -> str` helper used by both `scripts/review/audit.py` and `scripts/review/engines/argon.py`.
- **Acceptance Criteria**:
  - `AC-044-1`: `extract_issue_description()` in `scripts/review/models.py` resolves `description` or fallback keys (`details`, `message`, `summary`, `finding`, `title`, `comment`, `text`, `note`, `explanation`, `problem`, `issue`, `reason`, `defect`, `desc`).
  - `AC-044-2`: All existing and new unit tests pass (`pytest -v`).
