# Swift and Kotlin (Android) single-agent code-review linters, configs, and conventions

- Feature ID: 2026-11-18-mobile-kotlin-swift-code-review
- Type: enhancement
- Status: In-Testing
- First entered In-Testing: 2026-11-18
- Related specifications: Implemented: Changes [2026-11-18-single-agent-code-review](../2026-11-18-single-agent-code-review/spec.md)

## Problem and source intent

User requests:
1. "for the ai-review-plugin, I think there still some other languages like swift, kotlin (for android) what do you think"
2. "and I think that this new languages is some extend to an existing requirement, did the spec reflect it?"
3. "yes go with option 1, show me the updated plan" (scoping the linked delta package strictly to Swift and Kotlin/Android).

Grounding against `2026-11-18-single-agent-code-review` (`First entered In-Testing: 2026-11-18`), `skills/code-review/scripts/{prepare_code_review,lint_runner}.py`, and `scripts/review/rules/rule_docs/{kotlin,swift}.md` identified three gaps:
1. `prepare_code_review.py::LOCKFILE_BASENAMES` omits `Package.resolved` (SwiftPM), `Podfile.lock` (CocoaPods), and `gradle.lockfile`.
2. `lint_runner.py` has zero convention discovery or read-only CLI linter execution for `.swift`, `.kt`, or `.kts` files (`swiftlint`, `swift-format`, `ktlint`, `detekt`, or `--deep-lint` Gradle/SwiftPM checks).
3. `kotlin.md` (`4.8 KB`) lacks Official Kotlin / Android Kotlin Style, Android lifecycle/`Flow`, and Jetpack Compose rules—and lines 76–82 recommend `catch (e: Exception)` around `withContext(Dispatchers.IO)`, which swallows `CancellationException` and breaks structured concurrency—while `swift.md` (`8.0 KB`) omits Apple Swift API Design Guidelines, Google Swift Style Guide, and Swift Testing (`@Test`, `#expect`, `#require`).

## Repository grounding

- `skills/code-review/scripts/prepare_code_review.py`: `LOCKFILE_BASENAMES` (lines 31–43) filters lockfiles case-insensitively via `Path(p).name.lower()`.
- `skills/code-review/scripts/lint_runner.py`: `CONVENTION_FILES` (lines 14–51), `discover_repo_conventions()` (lines 69–119), `DIAG_LINE_RE` (line 64), and `run_scoped_linters()` (lines 289–385).
- `scripts/review/rules/system_rules.json` & `rule_docs/{kotlin,swift}.md`: Already maps `**/*.gradle.kts -> build_gradle.md` (line 8), `**/*.{kt,kts} -> kotlin.md` (line 25), and `**/*.swift -> swift.md` (line 44) across `57` rule docs (`tests/test_ocr_language_rules.py:58`).
- `skills/code-review/SKILL.md`: Documents convention precedence, executed CLI linters, and bundled industry convention packs.

## Non-goals

- Adding new `rule_docs/*.md` files (such as `dart.md` or `sql.md`) or altering `system_rules.json`'s 58 glob entries.
- Running file-mutating autofix flags (`swiftlint --fix`, `swift-format format -i`, `ktlint -F`).

## Requirements

### REQ-055: Mobile lockfile filtering for Swift and Kotlin/Gradle (`prepare_code_review.py`)

- Changes: [2026-11-18-single-agent-code-review/REQ-051](../2026-11-18-single-agent-code-review/spec.md#req-051-read-only-diff-and-language-rule-collector-prepare_code_reviewpy)
- Source intent: User selection ("yes go with option 1") extending `REQ-051`'s lockfile filtering to Swift and Kotlin/Android ecosystems.
- Previous contract: `LOCKFILE_BASENAMES` strips 9 web/backend lockfiles (`package-lock.json`..`gemfile.lock`) and leaves `Package.resolved`, `Podfile.lock`, and `gradle.lockfile` hunks in the diff.
- Statement: WHEN `prepare_code_review.py` filters unified diffs, `LOCKFILE_BASENAMES` SHALL additionally match `package.resolved`, `podfile.lock`, and `gradle.lockfile` case-insensitively, omitting their diff hunks while recording their paths in `skipped_lockfiles`.
- AC-055-1 — Success: Running `prepare_code_review.py` on a repo modifying `App.swift`, `MainViewModel.kt`, `Package.resolved`, `Podfile.lock`, and `gradle.lockfile` retains the `.swift` and `.kt` hunks (`matched_rules`: `swift.md`, `kotlin.md`) while omitting all three lockfile bodies and listing them in `skipped_lockfiles`.
- AC-055-2 — Boundary/failure: IF a diff modifies only `Package.resolved`, `Podfile.lock`, or `gradle.lockfile`, THEN `prepare_code_review.py` SHALL output an empty filtered diff body while listing the skipped lockfiles and leaving `.git/index` untouched.

### REQ-056: Swift and Kotlin/Android convention discovery and read-only scoped linters (`lint_runner.py` & `SKILL.md`)

- Changes: [2026-11-18-single-agent-code-review/REQ-052](../2026-11-18-single-agent-code-review/spec.md#req-052-repo-convention-auto-discovery-and-fast-read-only-scoped-linters-lint_runnerpy), [2026-11-18-single-agent-code-review/REQ-054](../2026-11-18-single-agent-code-review/spec.md#req-054-single-agent-skillmd-zero-repo-pollution-reporting-and-companion-rule-alignment)
- Source intent: User request ("swift, kotlin (for android)" -> "yes go with option 1") extending `REQ-052` and `REQ-054` to Swift and Kotlin/Android linters and configs.
- Previous contract: `lint_runner.py` and `skills/code-review/SKILL.md` do not discover Swift or Kotlin/Android configs or invoke CLI linters on `.swift`, `.kt`, or `.kts` files.
- Statement: WHEN `prepare_code_review.py` runs without `--no-lint`, `lint_runner.py` SHALL discover Swift and Kotlin/Android repository configs (`.swiftlint.yml`, `.swift-format`, `.swiftformat`, `Package.swift`, `detekt.yml`, `config/detekt/detekt.yml`, `lint.xml`, `gradle/libs.versions.toml`), execute installed fast read-only CLI linters scoped to changed files (`swiftlint lint --quiet -- <swift_files>`, `swift-format lint <swift_files>`, `ktlint --relative <kt_files>`, and `detekt --input <comma_joined_kt_files>` with `-c <detekt_cfg>` when present), emit `deep_lint_hints` and gate `gradle check -x test --no-daemon` (for Kotlin Gradle repos) and `swift build --build-tests` (for `Package.swift` repos) behind `--deep-lint`, and document these linters/conventions in `skills/code-review/SKILL.md`.
- AC-056-1 — Success: `discover_repo_conventions()` reports Swift/Kotlin config files (`swift_configs`, `kotlin_configs`, and Gradle/`Package.swift` `deep_lint_hints`); `run_scoped_linters()` executes available/stubbed `swiftlint`, `swift-format`, `ktlint`, and `detekt` on changed `.swift`/`.kt` files with accurate `in_diff_hunk` tagging; and `--deep-lint` runs `gradle check -x test --no-daemon` and `swift build --build-tests` when their build manifests exist.
- AC-056-2 — Boundary/failure: IF any Swift or Kotlin linter binary is missing from `PATH` or exceeds `timeout_sec`, THEN `run_scoped_linters()` SHALL record the skip/timeout in `skipped` without error and SHALL never invoke mutating formatter flags.

### REQ-057: Distilled Kotlin (Android + Coroutines + Compose) and Swift (API Design + Swift Testing) convention packs

- Changes: [2026-11-18-single-agent-code-review/REQ-053](../2026-11-18-single-agent-code-review/spec.md#req-053-distilled-industry-coding-conventions-across-core-rule_docsmd)
- Source intent: User request ("swift, kotlin (for android)" -> "yes go with option 1") and observed `CancellationException`-swallowing defect in `scripts/review/rules/rule_docs/kotlin.md:76-82`.
- Previous contract: `REQ-053` enriches only `java.md`, `go.md`, `python.md`, `ts_js_tsx_jsx.md`, and `rust.md`; `kotlin.md` lacks Android/Compose/Flow guidance and shows `catch (e: Exception)` swallowing `CancellationException`, while `swift.md` omits Apple Swift API Design Guidelines / Google Swift Style and Swift Testing (`@Test`, `#expect`, `#require`).
- Statement: WHEN `rule_matcher.py` resolves `kotlin.md` or `swift.md`, THE corpus SHALL preserve all `57` `rule_docs/*.md` files while replacing `kotlin.md` with a precision-first checklist covering Official Kotlin Coding Conventions + Android Kotlin Style Guide, Coroutine structured concurrency & `CancellationException` rethrow (`runCatching` trap), Android `Lifecycle`/`Flow` collection (`repeatOnLifecycle(STARTED)` / `collectAsStateWithLifecycle`), Android `ViewModel` `Context`/`View` leak & `PendingIntent` `FLAG_IMMUTABLE` safety, Jetpack Compose state/stability/side-effect rules, and `runTest`/Turbine/MockK test hygiene, and enriching `swift.md` with Apple Swift API Design Guidelines + Google Swift Style Guide and Swift Testing (`@Test`, `#expect`, `#require`).
- AC-057-1 — Success: `kotlin.md` includes the Official Kotlin + Android Kotlin Style, Coroutines/`CancellationException`, Android Lifecycle/`Flow`, Jetpack Compose, and Kotlin/Android Test Hygiene sections (removing the `catch (e: Exception)` coroutine anti-pattern); `swift.md` includes Apple Swift API Design Guidelines / Google Swift Style and Swift Testing sections while preserving `#### Swift Review Principles`; and `tests/test_ocr_language_rules.py` (`57` rule docs, `58` globs) passes.
- AC-057-2 — Boundary/failure: IF a diff touches both `app/build.gradle.kts` and `app/src/main/java/com/example/MainViewModel.kt`, THEN `resolve_rules_for_paths()` SHALL continue resolving `app/build.gradle.kts` to `build_gradle.md` and `MainViewModel.kt` to `kotlin.md`.

## Assumptions and owner-deferred questions

None.

## Approvals and lifecycle history

- 2026-11-18 (`Planning -> In-Progress`): User approved `implementation_plan.md` ("proceed") for `REQ-055`..`REQ-057` (Swift and Kotlin/Android lockfiles, configs, scoped linters, and distilled convention packs).
- 2026-11-18 (`In-Progress -> In-Testing`): Tasks 1 and 2 completed (`185/185` tests, `100.0%` and `94.7%` mutation kill rates, `Approved` code review); recorded [Run 1](./verification.md#run-1--2026-11-18).
