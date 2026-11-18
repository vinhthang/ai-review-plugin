# Design: Single-agent code-review skill, local scoped linters, and industry coding conventions

Sources: [spec.md](./spec.md), [decisions.md](./decisions.md)

## Components

| Requirement / AC | Path and symbol | Responsibility / change |
| --- | --- | --- |
| REQ-051 / AC-051-1, AC-051-2 | `skills/code-review/scripts/prepare_code_review.py::collect_review_bundle`, `main` | Capture unified diff via isolated `GIT_INDEX_FILE` (`default`, `--staged`, `--base`, `--diff-file`), strip lockfile bodies, parse changed line numbers per file, and resolve `<language_review_rules>` via `scripts/review/rule_matcher.py`. |
| REQ-052 / AC-052-1, AC-052-2 | `skills/code-review/scripts/lint_runner.py::discover_repo_conventions`, `run_scoped_linters` | Detect repo style/linter configs and language versions (`go.mod`, `checkstyle.xml`, `.golangci.yml`, `pyproject.toml`, `.editorconfig`), run `git diff --check` + fast read-only CLI linters on `PATH` (and `--deep-lint` build linters when opted in), and tag `in_diff_hunk` findings. |
| REQ-053 / AC-053-1, AC-053-2 | `scripts/review/rules/rule_docs/{java,go,python,ts_js_tsx_jsx,rust}.md` | Add distilled Google Java + Effective Java 3e, Google/Uber Go + active `*_test.go` checks, PEP 8 / Google Python, Google TS, and Rust API Guidelines sections while keeping all 57 rule files intact. |
| REQ-054 / AC-054-1, AC-054-2 | `skills/code-review/SKILL.md`, `rules/AGENTS.md`, `README.md`, `~/.gemini/config/rules/tdd.md`, `~/.codex/skills/code-review` | Replace subagent/`peer_review.py` workflow with single-agent zero-repo-pollution review, align companion governance rules, remove stale `< 500` lines note from `README.md`, and symlink `~/.codex/skills/code-review`. |

## Interfaces and flow

- `prepare_code_review.py` CLI:
  `python3 skills/code-review/scripts/prepare_code_review.py [--repo <dir>] [--staged | --base <ref> | --diff-file <file>] [--no-lint] [--deep-lint] [--dimension <all|inv|dom>] [--max-diff-chars <N>] [--json] [paths...]`
- `collect_review_bundle(...) -> dict`: Returns `{"empty_diff": bool, "changed_files": [...], "skipped_lockfiles": [...], "matched_rules": [...], "repo_conventions": {...}, "linters": {"findings": [...], "executed": [...], "skipped": [...]}, "dimension": str, "language_rules_context": str, "diff": str, "diff_truncated": bool}`.
- `discover_repo_conventions(repo_root: Path, changed_files: list[str]) -> dict`: Inspects repo root for config files and extracts `go_version` from `go.mod`, `python_tools` from `pyproject.toml`, and Java checkstyle/spotbugs/pmd config paths.
- `run_scoped_linters(repo_root: Path, changed_files: list[str], changed_lines_by_file: dict[str, set[int]], *, deep_lint: bool = False, timeout_sec: int = 15) -> dict`: Runs read-only commands with `subprocess.run(..., timeout=timeout_sec)`, parses `file:line` diagnostics where present to compute `in_diff_hunk`, and never modifies files.

## Boundaries and recovery

- Temporary git index safety: `prepare_code_review.py` creates a temp path via `tempfile.mkstemp(prefix="agy_cr_idx_")`, closes and unlinks the empty placeholder before git writes the index, passes `GIT_INDEX_FILE` only in the child `env` dict (never mutating `os.environ` or `.git/index`), and removes the temp index file in `finally:`.
- Lockfile and huge-diff protection: Lockfiles (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `Cargo.lock`, `poetry.lock`, `uv.lock`, `go.sum`) are listed in `skipped_lockfiles` and excluded from hunk expansion so large dependency updates do not drown out source hunks; `--max-diff-chars` (default `120000`) truncates oversized diffs cleanly with `diff_truncated: true`.
- Missing or slow linters: Missing binaries append `"<tool> (not installed)"` to `linters.skipped`; `subprocess.TimeoutExpired` kills the child process and appends `"<tool> (timed out after Ns)"` without aborting the review bundle.

## Dependencies and unresolved design work

None.
