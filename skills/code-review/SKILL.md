---
name: code-review
description: Perform a fast, single-agent peer review on code changes using local read-only linters, repository config auto-discovery, and distilled industry coding conventions without spawning external agents or polluting the repository.
---

# Code Review

Review uncommitted changes, staged diffs, or branch comparisons directly inside the current agent. Execute the entire review in-process—do not spawn subagents, timers, or external review engines, and do not write `review.md`, `review.json`, or `docs/adr/` files into the repository.

## 1. Collect Diff, Repo Conventions & Scoped Lints

Run the read-only collector from this skill's directory (`<skill-dir>/scripts/prepare_code_review.py`; prefix with `rtk` when `RULE[rtk.md]` is active):

```bash
python3 <skill-dir>/scripts/prepare_code_review.py --repo .
```

Common flags:
- `--staged` — review staged index changes only.
- `--base <ref>` — review changes relative to `<ref>` (e.g., `--base main`, `--base HEAD~1`).
- `--diff-file <path>` — review a pre-generated unified diff/patch file.
- `--deep-lint` — opt in to heavier build-tool linters (`mvn`/`gradle` Checkstyle/SpotBugs/Detekt/Android Lint, `cargo clippy`, `swift build --build-tests`) when requested by the user.
- `--no-lint` — skip local CLI linters when only diff + convention rules are needed.
- `--dimension <all|inv|dom>` — focus on structural invariants (`inv`) or domain completeness (`dom`).
- `[paths...]` — restrict review to specific files or directories.

If the output reports `Empty Diff: true` (no changes to review), state clearly in chat that no modifications were detected and stop.

## 2. Apply Convention & Linter Precedence

Evaluate changes in strict priority order so outside conventions never fight a repository's own standards:

1. **Repository-Local Configuration (`repo_conventions`)**: Honor project configs discovered in the repo root first (`CONTRIBUTING.md`, `STYLEGUIDE.md`, `.editorconfig`, `checkstyle.xml`, `pmd.xml`, `detekt.yml`, `lint.xml`, `.swiftlint.yml`, `.swift-format`, `Package.swift`, `.golangci.yml`, `go.mod` Go version, `pyproject.toml`, `tsconfig.json`, `biome.json`, `eslint` config).
2. **Deterministic Scoped Lints (`linters`)**: Treat real errors reported by `git diff --check` and local CLI linters (`gofmt`, `go vet`, `golangci-lint`/`staticcheck`, `checkstyle`, `pmd`, `ktlint`, `detekt`, `swiftlint`, `swift-format`, `ruff`, `rustfmt`, `shellcheck`, `biome`/`eslint`, `actionlint`) on changed hunks (`in_diff_hunk=true`) as verified evidence; treat pre-existing warnings outside changed hunks as context only.
3. **Bundled Industry Coding Conventions (`<language_review_rules>`)**: Apply the matched language checklists returned by the collector—including Google Java Style + *Effective Java* (3rd Ed.) + Spring Boot test-annotation/Testcontainer discipline (`java.md`), Official Kotlin + Android Kotlin Style + Coroutines/Jetpack Compose/Android lifecycle discipline (`kotlin.md`), Apple Swift API Design Guidelines + Google Swift Style + Swift 6 concurrency/ARC/SwiftUI/Swift Testing (`swift.md`), Google Go + Uber Go Style + `*_test.go` rules (`go.md`), PEP 8 + Google Python Style (`python.md`), Google TypeScript Style (`ts_js_tsx_jsx.md`), and Rust API Guidelines (`rust.md`).
4. **On-Demand External Lookup (Fallback Only)**: Only search external docs or the web when `matched_rules` falls back to `default.md` or touches a specialized framework not covered by the bundled checklists.

## 3. Verify Context Before Flagging (`Ground A` & `Ground B`)

Favor precision over recall—a false alarm erodes trust faster than silence on minor style preferences:

- **Ground A (Diff Scope Invariant)**: Only report defects introduced, modified, or broken by the changed hunks. Never nitpick untouched legacy lines outside the diff.
- **Ground B (Caller & Diff Verification)**: Before emitting any finding:
  1. Re-check the diff hunks to confirm no line already handles the case (imports, guards, cleanup, tests).
  2. Inspect surrounding callers, callees, upstream type/null contracts, and enclosing locks or `with`/`try-with-resources` blocks (using CodeGraph tools if `.codegraph/` is active, otherwise file-reading / AST tools). Never infer concurrency, attacker control, or nullability from a function name alone.
- **Docs vs. Code Guardrail**: When reviewing Markdown or skill files (`*.md`), evaluate contract clarity, link/CLI accuracy, and consistency—never demand that shell scripts or sanitizers be inlined into prose documentation.

## 4. Severity Rubric & Direct Report

Classify every verified finding strictly:
- **P0 (Critical — Blocking)**: Exploitable security flaws, data loss/corruption, crashes/panics on reachable inputs, auth/permission bypasses, deadlocks.
- **P1 (Defect — Blocking)**: Incorrect business/boundary logic, dropped errors, race conditions, resource leaks, broken caller contracts, vacuous/self-mocked tests, or blocking framework test-hygiene violations (such as combining `@UnitTest` + `@IntegrationTest`, mocking `*Repository` inside `@IntegrationTest`, or calling `t.Fatal`/`require.*` inside a Go child goroutine).
- **P2 (Advisory — Non-Blocking)**: Idiomatic convention improvements, naming clarity, minor maintainability or style suggestions.

Present the review **directly in chat** (use a Brain Artifact only when an extensive multi-module report is requested—never write files into the repository):

1. **Verdict**: `Approved` (`0` P0/P1 issues) or `Changes Requested` (`N` blocking P0/P1 issues).
2. **Blocking Issues (`P0` / `P1`)**: File link with exact line range, severity, concrete failure scenario, and minimal fix.
3. **Advisory Notes (`P2`)**: Concise non-blocking suggestions (omit section if none).
4. **Checked Scope**: Changed file count, matched convention packs, and executed/skipped local linters.
