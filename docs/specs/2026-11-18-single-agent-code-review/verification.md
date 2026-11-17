# Verification: Single-agent code-review skill, local scoped linters, and industry coding conventions

Governing specification: [spec.md](./spec.md)

## Planned checks

### AC-051-1 (REQ-051)

- Method: Unit tests in `tests/test_prepare_code_review.py` exercising `prepare_code_review.py` across uncommitted (staged + unstaged + untracked), `--staged`, `--base`, unborn `HEAD`, and symlinked `~/.codex/skills/code-review` invocations while asserting `.git/index` SHA-256 and `git status --porcelain` invariance.
- Expected outcome: Returns `empty_diff: false`, accurate changed file lists, deduplicated `python.md`/`java.md`/`go.md` rules, and unified diff text with zero `.git/index` or working-tree mutation.
- Execution: [Run 1](#run-1--2026-11-18)

### AC-051-2 (REQ-051)

- Method: Boundary unit tests in `tests/test_prepare_code_review.py` covering clean repositories (`empty_diff: true`), lockfile-only / mixed lockfile changes (`package-lock.json`, `Cargo.lock`, `uv.lock`), and invalid `--repo` / `--base` arguments.
- Expected outcome: Clean repos return `empty_diff: true`; lockfile hunks are excluded from `diff` and listed in `skipped_lockfiles`; invalid refs/dirs fail cleanly with zero leftover `agy_cr_idx_*` temp files.
- Execution: [Run 1](#run-1--2026-11-18)

### AC-052-1 (REQ-052)

- Method: Unit tests in `tests/test_prepare_code_review.py` testing `discover_repo_conventions()` (`go.mod` version, `.golangci.yml`, `checkstyle.xml`, `pyproject.toml`, `.editorconfig`) and `run_scoped_linters()` (`git diff --check` + real/stubbed CLI linters on `PATH` and `--deep-lint` build-tool gating).
- Expected outcome: Repo conventions and Go version are extracted accurately; linter diagnostics carry `in_diff_hunk` booleans; build-tool linters only run when `deep_lint=True`.
- Execution: [Run 1](#run-1--2026-11-18)

### AC-052-2 (REQ-052)

- Method: Fault-injection unit tests in `tests/test_prepare_code_review.py` with minimal `PATH` (missing linters) and a slow stub linter exceeding `timeout_sec=1`.
- Expected outcome: Missing binaries and timed-out linters are recorded in `linters.skipped` without raising unhandled exceptions or mutating files.
- Execution: [Run 1](#run-1--2026-11-18)

### AC-053-1 (REQ-053)

- Method: Run `tests/test_ocr_language_rules.py` and `tests/test_prepare_code_review.py` assertions inspecting `java.md`, `go.md`, `python.md`, `ts_js_tsx_jsx.md`, and `rust.md`.
- Expected outcome: All 57 `rule_docs/*.md` files exist and pass `TestOcrLanguageRules`; `java.md` includes Google Java + Effective Java 3e + 5 Spring Boot test rules; `go.md` includes Google/Uber Go style and reviews `*_test.go` files.
- Execution: [Run 1](#run-1--2026-11-18)

### AC-053-2 (REQ-053)

- Method: Inspect `skills/code-review/SKILL.md` and `tests/test_prepare_code_review.py` fallback check on unknown extensions (`default.md`).
- Expected outcome: `SKILL.md` specifies convention precedence and permits external web/doc lookup only when `matched_rules` falls back to `default.md` or lacks framework conventions.
- Execution: [Run 1](#run-1--2026-11-18)

### AC-054-1 (REQ-054)

- Method: Packaging/assertion checks in `tests/test_prepare_code_review.py` plus CLI runs of `surface_validator.py`, `agy plugin validate`, Codex `quick_validate.py`, and live dogfood execution of `prepare_code_review.py` on `ai-review-plugin`.
- Expected outcome: Zero subagent/`peer_review.py`/repo-pollution instructions in `skills/code-review/SKILL.md`; `~/.codex/skills/code-review` symlink valid; `rules/AGENTS.md` and `~/.gemini/config/rules/tdd.md` aligned; all validators exit `0`.
- Execution: [Run 1](#run-1--2026-11-18)

### AC-054-2 (REQ-054)

- Method: Run `surface_validator.py --plugin-dir ~/.gemini/config/plugins/ai-review-plugin --json`.
- Expected outcome: Exits `0` with `"valid": true`, `"errors": []`, all 3 skill triggers (`spec-review`, `design-review`, `code-review`) present, and `always_on_chars <= 8000`.
- Execution: [Run 1](#run-1--2026-11-18)

## Execution evidence

### Run 1 — 2026-11-18

- Scope: `AC-051-1`, `AC-051-2`, `AC-052-1`, `AC-052-2`, `AC-053-1`, `AC-053-2`, `AC-054-1`, `AC-054-2`
- Commands:
  - `PYTHONDONTWRITEBYTECODE=1 rtk pytest -p no:cacheprovider tests/` -> `182 passed, 0 failed`
  - `mutation_runner.py` -> `skills/code-review/scripts/lint_runner.py` `100.0% (8/8)`, `skills/code-review/scripts/prepare_code_review.py` `94.7% (18/19)`
  - `rtk python3 ~/.codex/skills/code-review/scripts/prepare_code_review.py --repo ~/.gemini/config/plugins/ai-review-plugin skills/code-review rules/AGENTS.md plugin.json` -> `exit 0` (`Empty Diff: false`, `0` lint defects, `json.md`/`default.md`/`python.md` loaded via Codex symlink)
  - `surface_validator.py --plugin-dir ~/.gemini/config/plugins/ai-review-plugin` -> `Plugin surface valid (3 skills, 1707/8000 always-on chars)`
  - `agy plugin validate` -> `Validation passed (0 warnings)`
  - `quick_validate.py ~/.codex/skills/code-review` -> `Skill is valid!`
- Result: `AC-051-1` PASS, `AC-051-2` PASS, `AC-052-1` PASS, `AC-052-2` PASS, `AC-053-1` PASS, `AC-053-2` PASS, `AC-054-1` PASS, `AC-054-2` PASS

## Real-world observations

No real-world confirmation has been recorded.
