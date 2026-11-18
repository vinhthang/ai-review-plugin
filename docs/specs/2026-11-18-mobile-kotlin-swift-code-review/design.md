# Design: Swift and Kotlin (Android) single-agent code-review linters, configs, and conventions

Sources: [spec.md](./spec.md), [decisions.md](./decisions.md)

## Components

| Requirement / AC | Path and symbol | Responsibility / change |
| --- | --- | --- |
| REQ-055 / AC-055-1, AC-055-2 | `skills/code-review/scripts/prepare_code_review.py::LOCKFILE_BASENAMES` | Add `"package.resolved"`, `"podfile.lock"`, and `"gradle.lockfile"` to case-insensitive lockfile stripping. |
| REQ-056 / AC-056-1, AC-056-2 | `skills/code-review/scripts/lint_runner.py::{CONVENTION_FILES, discover_repo_conventions, run_scoped_linters}` | Add Swift/Kotlin/Android config discovery (`swift_configs`, `kotlin_configs`, `deep_lint_hints`), fast read-only `swiftlint`, `swift-format`, `ktlint`, and `detekt` jobs, and `--deep-lint` Gradle/SwiftPM jobs. |
| REQ-056 / AC-056-1, AC-056-2 | `skills/code-review/SKILL.md` | Document Swift and Kotlin/Android repo configs, CLI linters, and bundled convention packs. |
| REQ-057 / AC-057-1, AC-057-2 | `scripts/review/rules/rule_docs/kotlin.md` | Replace tutorial snippets (including the `CancellationException`-swallowing `catch (e: Exception)`) with Official Kotlin + Android Kotlin Style, Coroutines/`Flow`, Android lifecycle/memory/security, Jetpack Compose, and `runTest`/Turbine/MockK checklists. |
| REQ-057 / AC-057-1, AC-057-2 | `scripts/review/rules/rule_docs/swift.md` | Add Apple Swift API Design Guidelines + Google Swift Style and Swift Testing (`@Test`, `#expect`, `#require`) sections while preserving `#### Swift Review Principles` and runtime/SwiftUI/concurrency rules. |

## Interfaces and flow

- `discover_repo_conventions(repo_root, changed_files)` extends its returned dict with:
  - `swift_configs`: `{"swiftlint": ".swiftlint.yml", "swift_format": ".swift-format" | ".swiftformat"}` when present.
  - `kotlin_configs`: `{"detekt": "detekt.yml" | "config/detekt/detekt.yml", "android_lint": "lint.xml"}` when present.
  - `deep_lint_hints`: appends Gradle hint when `.kt`/`.kts` files change alongside `build.gradle`/`build.gradle.kts`, and SwiftPM hint when `.swift` files change alongside `Package.swift`.
- `run_scoped_linters(...)` collects `swift_files` (`*.swift`) and `kt_files` (`*.kt`, `*.kts`):
  - Default fast jobs (`timeout_sec = 15`):
    - `swiftlint`: `["swiftlint", "lint", "--quiet", "--", *swift_files]`
    - `swift-format`: `["swift-format", "lint", *swift_files]`
    - `ktlint`: `["ktlint", "--relative", *kt_files]`
    - `detekt`: `["detekt", "--input", ",".join(kt_files), *(["-c", detekt_cfg] if detekt_cfg else [])]`
  - Opt-in `--deep-lint` jobs (`deep_timeout = max(timeout_sec, 60)`):
    - Kotlin/Java Gradle: `["gradle", "check", "-x", "test", "--no-daemon"]` (single deduplicated job when `(java_files or kt_files)` and `build.gradle`/`build.gradle.kts` exist).
    - SwiftPM: `["swift", "build", "--build-tests"]` when `swift_files` and `Package.swift` exist.

## Boundaries and recovery

- Missing CLI binaries (`swiftlint`, `swift-format`, `ktlint`, `detekt`, `swift`, `gradle`) or timeouts (`> timeout_sec`) are recorded in `skipped` by `_run_tool()` without raising exceptions or mutating working-tree files.
- `DIAG_LINE_RE` (`^(.+?):(\d+)(?::\d+)?:\s*(.+)$`) already parses `file:line:col: warning: message` (`swiftlint`, `swift-format`) and `file:line:col: message` (`ktlint`, `detekt`) into normalized repo-relative findings tagged with `in_diff_hunk`.
- `system_rules.json` keeps `"**/*.gradle.kts": "build_gradle.md"` ahead of `"**/*.{kt,kts}": "kotlin.md"`, preserving Gradle script specificity and `REQ-048`'s `57`-file count.

## Dependencies and unresolved design work

None.
