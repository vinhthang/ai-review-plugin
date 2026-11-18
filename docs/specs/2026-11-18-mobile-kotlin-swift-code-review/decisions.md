# Decisions: Swift and Kotlin (Android) single-agent code-review linters, configs, and conventions

Governing specification: [spec.md](./spec.md)

## Architectural rationale

- Governs: REQ-055, REQ-056, REQ-057

Existing accepted decisions `ADR-042` (offline distilled convention packs with repo-config precedence) and `ADR-043` (fast read-only standalone CLI linters by default with opt-in `--deep-lint` for slow build tools) in [2026-11-18-single-agent-code-review/decisions.md](../2026-11-18-single-agent-code-review/decisions.md), combined with `REQ-048`'s `57`-file `rule_docs/` invariant and `2026-11-18-single-agent-code-review`'s frozen `First entered In-Testing: 2026-11-18` history, constrain the design to one clean approach:
1. Model the extension as a linked delta package (`REQ-055`..`REQ-057`, `Changes REQ-051..REQ-054`) rather than mutating frozen `REQ-051`..`REQ-053` bodies in place.
2. Enrich `kotlin.md` and `swift.md` in place inside `scripts/review/rules/rule_docs/` so `system_rules.json` (`58` globs) and `rule_docs/` (`57` files) remain 100% compatible with `REQ-048` and `~/.codex/skills/code-review`.
3. Run standalone `swiftlint`, `swift-format`, `ktlint`, and `detekt` in read-only mode on changed files with a `15s` timeout by default, while keeping slow Gradle (`gradle check -x test --no-daemon`) and SwiftPM (`swift build --build-tests`) invocations strictly behind `--deep-lint`.

## Gate 1: normative review

| Check | Status | Evidence / required correction |
| --- | --- | --- |
| Codebase grounding | PASS | Inspected `prepare_code_review.py`, `lint_runner.py`, `system_rules.json`, `rule_docs/{kotlin,swift,java}.md`, `tests/test_ocr_language_rules.py`, and `tests/test_prepare_code_review.py`. |
| Attributable intent and explicit scope | PASS | `REQ-055`..`REQ-057` trace directly to user prompts ("swift, kotlin (for android)", "yes go with option 1") and the verified `CancellationException` bug in `kotlin.md:76-82`; `Non-goals` exclude Dart/SQL and mutating autofixes. |
| Observable requirements and meaningful acceptance criteria | PASS | Every requirement has deterministic success and boundary/failure acceptance criteria (`AC-055-1`..`AC-057-2`). |
| Assumptions and owner-deferred questions are explicit | PASS | Zero open or `[PROVISIONAL]` questions remain after user selected Option 1. |
| Architectural rationale respects requirements | PASS | Constrained by accepted `ADR-042`/`ADR-043` and `REQ-048` without strawman ADRs. |
| IDs, references, and revision route are consistent | PASS | Allocates `REQ-055`..`REQ-057` above `REQ-054` as a linked `Proposed: Changes` delta against `2026-11-18-single-agent-code-review`. |
