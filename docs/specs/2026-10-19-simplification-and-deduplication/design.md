# Architectural Design: Codebase Simplification, Deduplication & Modularization

- **Feature ID**: `2026-10-19-simplification-and-deduplication`
- **Status**: `Planning`
- **Addresses**: `REQ-041`, `REQ-042`, `REQ-043`, `REQ-044`

## 1. Rule Deduplication & Escaped-Pipe Table Governance (`REQ-041`)

- Delete `ai-review-plugin/rules/spec-standard.md` (and empty `rules/` directory if applicable) so `spec-driven-plugin/rules/spec-standard.md` is the sole loaded specification rule.
- Synchronize `scripts/spec_checker.py` from `spec-driven-plugin/scripts/spec_checker.py` (with `parse_specs_index_text()`, `resolve_package_dir()`, and standard `parser.add_argument` calls for `--feature`, `--allow-planning`, and `--verify-evidence`).
- In `scripts/review/governance.py` (`update_index_catalog()`):
  ```python
  trimmed = row.strip()
  raw_cols = re.split(r"(?<!\\)\|", trimmed[1:-1])
  cols = [col.strip() for col in raw_cols]
  ```

---

## 2. `scripts/review/audit.py` & `scripts/review/prompts.py` (`REQ-042`)

- Create `scripts/review/prompts.py` containing `build_review_prompt(...) -> str`, encapsulating the `spec`, `design`, and `code` mode prompt instructions, diagnostic context injection, prior-review rebuttal checklist, and ADR embedding.
- In `scripts/review/audit.py`, extract:
  - `prepare_repo_sandbox(repo: str, work_dir: str) -> str`: Handles `rsync` with fallback to `shutil.copytree`.
  - `execute_engine_process(cmd: List[str], repo_copy: str, env: Dict[str, str], fout_path: str, ferr_path: str, engine_name: str) -> None`: Handles `subprocess.Popen`, 1800s timeout, and `SIGTERM`/`SIGKILL` cleanup.
- Reduces `scripts/review/audit.py` from 509 lines to ~300 lines.

---

## 3. `scripts/review/runners/cdp_client.py` Extraction (`REQ-043`)

- Move `CDPClient` (`L37–L233` of `edge_applescript_runner.py`) into `scripts/review/runners/cdp_client.py`.
- Import `from review.runners.cdp_client import CDPClient` in `edge_applescript_runner.py` so all existing imports (`from review.runners.edge_applescript_runner import CDPClient`) continue to work unchanged.
- Reduces `edge_applescript_runner.py` from 536 lines to ~340 lines and keeps `cdp_client.py` at ~210 lines.

---

## 4. Shared Issue Description Helper in `scripts/review/models.py` (`REQ-044`)

- Add `ISSUE_DESC_FALLBACK_KEYS = ("details", "message", "summary", "finding", "title", "comment", "text", "note", "explanation", "problem", "issue", "reason", "defect", "desc")` and `extract_issue_description(item: Dict[str, Any]) -> str` in `scripts/review/models.py`.
- Call `extract_issue_description(item)` in both `scripts/review/audit.py` and `scripts/review/engines/argon.py`.
