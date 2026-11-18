# Tasks: Swift and Kotlin (Android) single-agent code-review linters, configs, and conventions

Sources: [spec.md](./spec.md), [design.md](./design.md)

## Task 1: Overhaul `kotlin.md` (Android + Coroutines + Compose) and enrich `swift.md` + `SKILL.md`

- [x] Complete the work and its applicable checks.
- Covers: REQ-056 / AC-056-1; REQ-057 / AC-057-1, AC-057-2
- Files: `scripts/review/rules/rule_docs/kotlin.md`, `scripts/review/rules/rule_docs/swift.md`, `skills/code-review/SKILL.md`, `tests/test_ocr_language_rules.py`
- Dependencies: None
- Blocked by: None
- Work: Write failing assertions in `tests/test_ocr_language_rules.py` verifying `kotlin.md` (Official Kotlin + Android Kotlin Style, `CancellationException` rethrow, Android `Lifecycle`/`Flow` `repeatOnLifecycle`/`collectAsStateWithLifecycle`, Jetpack Compose stability/side-effects, `ViewModel` leak/`PendingIntent` safety, `runTest`/Turbine/MockK, and absence of `catch (e: Exception)` swallowing) and `swift.md` (Apple Swift API Design Guidelines, Google Swift Style, Swift Testing `@Test`/`#expect`); update `kotlin.md`, `swift.md`, and `skills/code-review/SKILL.md`; verify `tests/test_ocr_language_rules.py` (`57` rule docs, `58` globs).
- Completion evidence: Completed in [Run 1](./verification.md#run-1--2026-11-18) (`test_ocr_language_rules.py` `5/5` passed; `57` rule docs and `58` globs preserved).

## Task 2: Add Swift and Kotlin/Android lockfile filtering, config discovery, and read-only scoped linters

- [x] Complete the work and its applicable checks.
- Covers: REQ-055 / AC-055-1, AC-055-2; REQ-056 / AC-056-1, AC-056-2
- Files: `skills/code-review/scripts/prepare_code_review.py`, `skills/code-review/scripts/lint_runner.py`, `tests/test_prepare_code_review.py`
- Dependencies: None
- Blocked by: None
- Work: Write failing TDD tests in `tests/test_prepare_code_review.py` covering `Package.resolved`/`Podfile.lock`/`gradle.lockfile` stripping, `.swiftlint.yml`/`.swift-format`/`detekt.yml`/`lint.xml` convention discovery, stubbed `swiftlint`/`swift-format`/`ktlint`/`detekt` `in_diff_hunk` diagnostics, missing/timeout skips, and `--deep-lint` Gradle/SwiftPM gating; implement changes in `prepare_code_review.py` and `lint_runner.py`; run full `pytest`, `mutation_runner.py` (`>= 80%`), and single-agent `code-review`.
- Completion evidence: Completed in [Run 1](./verification.md#run-1--2026-11-18) (`185/185` tests passing, `100.0%` `lint_runner.py` and `94.7%` `prepare_code_review.py` mutation kill rates, `Approved` code review).

## Gate 2: traceability and readiness

| Requirement | AC | ADR or rationale | Design | Task | Planned verification | Status / reason |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-055 | AC-055-1 | [Rationale](./decisions.md#architectural-rationale) | [Components](./design.md#components) | [Task 2](#task-2-add-swift-and-kotlinandroid-lockfile-filtering-config-discovery-and-read-only-scoped-linters) | [AC-055-1](./verification.md#ac-055-1-req-055) | PASS — mobile lockfile stripping with `.swift`/`.kt` retention mapped |
| REQ-055 | AC-055-2 | [Rationale](./decisions.md#architectural-rationale) | [Components](./design.md#components) | [Task 2](#task-2-add-swift-and-kotlinandroid-lockfile-filtering-config-discovery-and-read-only-scoped-linters) | [AC-055-2](./verification.md#ac-055-2-req-055) | PASS — lockfile-only diff boundary mapped |
| REQ-056 | AC-056-1 | [Rationale](./decisions.md#architectural-rationale) | [Interfaces](./design.md#interfaces-and-flow) | [Task 1](#task-1-overhaul-kotlinmd-android--coroutines--compose-and-enrich-swiftmd--skillmd), [Task 2](#task-2-add-swift-and-kotlinandroid-lockfile-filtering-config-discovery-and-read-only-scoped-linters) | [AC-056-1](./verification.md#ac-056-1-req-056) | PASS — Swift/Kotlin config discovery, fast linters, and `--deep-lint` mapped |
| REQ-056 | AC-056-2 | [Rationale](./decisions.md#architectural-rationale) | [Boundaries](./design.md#boundaries-and-recovery) | [Task 2](#task-2-add-swift-and-kotlinandroid-lockfile-filtering-config-discovery-and-read-only-scoped-linters) | [AC-056-2](./verification.md#ac-056-2-req-056) | PASS — missing/timeout linter resilience and zero autofix flags mapped |
| REQ-057 | AC-057-1 | [Rationale](./decisions.md#architectural-rationale) | [Components](./design.md#components) | [Task 1](#task-1-overhaul-kotlinmd-android--coroutines--compose-and-enrich-swiftmd--skillmd) | [AC-057-1](./verification.md#ac-057-1-req-057) | PASS — `kotlin.md` Android/Compose/Coroutines overhaul and `swift.md` enrichment mapped |
| REQ-057 | AC-057-2 | [Rationale](./decisions.md#architectural-rationale) | [Boundaries](./design.md#boundaries-and-recovery) | [Task 1](#task-1-overhaul-kotlinmd-android--coroutines--compose-and-enrich-swiftmd--skillmd) | [AC-057-2](./verification.md#ac-057-2-req-057) | PASS — `build.gradle.kts` vs `.kt` specificity preservation mapped |

- Backward scope check: PASS — Task 1 and Task 2 have strictly disjoint `- Files:` write-sets and serve only `REQ-055`..`REQ-057`.
- Reference and catalog consistency: PASS — all links, anchors, and `docs/specs/INDEX.md` entries match.
