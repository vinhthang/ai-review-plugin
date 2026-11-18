# Verification: Swift and Kotlin (Android) single-agent code-review linters, configs, and conventions

Governing specification: [spec.md](./spec.md)

## Planned checks

### AC-055-1 (REQ-055)

- Method: Unit test in `tests/test_prepare_code_review.py` running `prepare_code_review.py --json` against a git repo modifying `App.swift`, `MainViewModel.kt`, `Package.resolved`, `Podfile.lock`, and `gradle.lockfile`.
- Expected outcome: `.swift` and `.kt` hunks and `matched_rules` (`swift.md`, `kotlin.md`) are retained while all three mobile lockfiles are omitted from `diff` and listed in `skipped_lockfiles`.
- Execution: PASS in [Run 1](#run-1--2026-11-18).

### AC-055-2 (REQ-055)

- Method: Unit test in `tests/test_prepare_code_review.py` modifying only `Package.resolved`, `Podfile.lock`, and `gradle.lockfile`.
- Expected outcome: Filtered `diff` is empty, `skipped_lockfiles` lists all three files, and `.git/index` remains byte-identical.
- Execution: PASS in [Run 1](#run-1--2026-11-18).

### AC-056-1 (REQ-056)

- Method: Unit tests in `tests/test_prepare_code_review.py` testing `discover_repo_conventions()` and `run_scoped_linters()` with `.swiftlint.yml`, `.swift-format`, `detekt.yml`, `lint.xml`, `Package.swift`, `build.gradle.kts`, and executable CLI stubs for `swiftlint`, `swift-format`, `ktlint`, `detekt`, `gradle`, and `swift`.
- Expected outcome: Repo configs and `deep_lint_hints` are reported; fast CLI linters run on changed `.swift`/`.kt` files with accurate `in_diff_hunk` tagging; `--deep-lint` runs `gradle check -x test --no-daemon` and `swift build --build-tests`; `skills/code-review/SKILL.md` documents the tools.
- Execution: PASS in [Run 1](#run-1--2026-11-18).

### AC-056-2 (REQ-056)

- Method: Boundary unit tests in `tests/test_prepare_code_review.py` running `run_scoped_linters()` with an empty `PATH` and with a hanging `swiftlint` stub (`timeout_sec=1`), plus inspecting constructed command argv for absence of `--fix`, `-F`, or `-i`.
- Expected outcome: Missing and timed-out binaries are recorded in `skipped` cleanly with zero exceptions and zero mutating flags.
- Execution: PASS in [Run 1](#run-1--2026-11-18).

### AC-057-1 (REQ-057)

- Method: Run `tests/test_ocr_language_rules.py` verifying `kotlin.md` and `swift.md` section headers, `CancellationException` guidance, absence of `catch (e: Exception) { /* handle exception */ }`, and `57`-file / `58`-glob corpus integrity.
- Expected outcome: All `tests/test_ocr_language_rules.py` assertions pass.
- Execution: PASS in [Run 1](#run-1--2026-11-18).

### AC-057-2 (REQ-057)

- Method: Glob specificity test in `tests/test_ocr_language_rules.py` passing `["app/build.gradle.kts", "app/src/main/kotlin/MainViewModel.kt", "ios/App.swift"]` to `resolve_rules_for_paths()`.
- Expected outcome: Resolves `["build_gradle.md", "kotlin.md", "swift.md"]` in order.
- Execution: PASS in [Run 1](#run-1--2026-11-18).

## Execution evidence

### Run 1 — 2026-11-18

- Environment: macOS, Python `3.11`, Antigravity `2.0`.
- Result: PASS (`AC-055-1`..`AC-057-2` passed).
- Full test suite (`PYTHONDONTWRITEBYTECODE=1 rtk pytest -p no:cacheprovider tests/ -q`): **`185 passed in 15.01s`** (`0` failed).
- Mutation testing (`mutation_runner.py`):
  - `skills/code-review/scripts/lint_runner.py`: **`100.0%` (`8/8` killed)**.
  - `skills/code-review/scripts/prepare_code_review.py`: **`94.7%` (`18/19` killed)**.
- Surface, plugin & code-review validation:
  - `surface_validator.py --plugin-dir .`: **`Plugin surface valid (3 skills, 1707/8000 always-on chars)`**.
  - `agy plugin validate`: **`Validation passed (skills 3 · rules 1)`**.
  - `prepare_code_review.py --repo .` + `git diff --check HEAD`: **`Approved` (`0` `P0`/`P1` defects, `0` whitespace warnings)**.

## Real-world observations

No real-world confirmation has been recorded.
