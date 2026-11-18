# Decisions: Single-agent code-review skill, local scoped linters, and industry coding conventions

Governing specification: [spec.md](./spec.md)

## Architectural rationale

- Governs: REQ-051, REQ-054

`REQ-051` and `REQ-054` follow directly from explicit user requirements ("no need to call other agent", zero repository pollution, and alignment of `rules/AGENTS.md` + `tdd.md`). Resolving `scripts/review/rule_matcher.py` via `Path(__file__).resolve().parents[3]` allows `skills/code-review` to be symlinked directly at `~/.codex/skills/code-review` without duplicating the 57 `rule_docs/*.md` files or breaking `REQ-048`'s file-count invariant.

## ADR-042: Offline distilled convention packs with repo-config precedence over live web fetching

- Governs: REQ-053
- State: Accepted
- Context and constraints: Code reviews need authoritative language standards (Google Java Style + Effective Java, Google/Uber Go, PEP 8 / Google Python, Google TS, Rust API Guidelines) without adding network latency, formatting noise, or breaking offline CLI sandboxes, and without violating project-local style configs or `REQ-048`'s 57-file `rule_docs/` invariant.
- Viable options:
  1. **Offline distilled conventions in existing `rule_docs/*.md` + repo-config discovery first:** Enrich `java.md`, `go.md`, `python.md`, `ts_js_tsx_jsx.md`, and `rust.md` in place with semantic/idiomatic rules from those standards, rank repo-local configs (`checkstyle.xml`, `.golangci.yml`, `go.mod`, `pyproject.toml`, `.editorconfig`) higher in precedence, and restrict web lookup to unbundled fallback languages.
  2. **Live web search on every review:** Fetch external style guide pages dynamically whenever `code-review` runs.
- Decision: Option 1 (offline distilled conventions + repo-config precedence, web lookup only on unbundled fallback).
- Costs and risks: Bundled checklists require occasional curation when major language versions ship; mitigated by auto-reading `go.mod` / `pyproject.toml` / `pom.xml` language versions in `discover_repo_conventions()`.
- Rejected alternatives: Option 2 adds 5–15s per review, wastes tokens on whitespace/brace rules handled by linters, and fails in network-isolated environments.
- Affected components: `scripts/review/rules/rule_docs/{java,go,python,ts_js_tsx_jsx,rust}.md`, `skills/code-review/scripts/lint_runner.py`, `skills/code-review/SKILL.md`.

## ADR-043: Fast read-only CLI linters by default with opt-in `--deep-lint` for build tools

- Governs: REQ-052
- State: Accepted
- Context and constraints: Asking an LLM to simulate `gofmt`, `go vet`, `golangci-lint`, `checkstyle`, or `ruff` misses deterministic diagnostics or hallucinates line numbers, while running full `mvn checkstyle:check spotbugs:check` or `cargo clippy` unconditionally takes 30–180s and triggers build side effects.
- Viable options:
  1. **Fast read-only CLI linters on changed files/packages by default + opt-in `--deep-lint`:** Automatically run fast standalone CLI linters found on `PATH` (`git diff --check`, `gofmt -l`, `go vet`, `golangci-lint`/`staticcheck`, `checkstyle`, `pmd`, `ruff`, `rustfmt --check`, `shellcheck`, `biome`/`eslint`, `actionlint`) with a short per-tool timeout (`15s`), skip missing binaries cleanly, and run `mvn`/`gradle`/`cargo clippy` only when `--deep-lint` is passed.
  2. **Unconditional build-tool linting on every review:** Run `mvn`/`gradle`/`cargo` checks on every invocation.
- Decision: Option 1 (fast standalone read-only CLI linters by default; `--deep-lint` opt-in for build-tool linters).
- Costs and risks: If a Java developer only has Maven Checkstyle configured without the standalone `checkstyle` CLI, default mode surfaces `checkstyle.xml` in `repo_conventions` and suggests `--deep-lint` rather than running Maven automatically.
- Rejected alternatives: Option 2 stalls quick reviews for minutes, requires network/artifact caches, and conflicts with fast interactive single-agent review.
- Affected components: `skills/code-review/scripts/lint_runner.py`, `skills/code-review/scripts/prepare_code_review.py`, `skills/code-review/SKILL.md`.

## Gate 1: normative review

| Check | Status | Evidence / required correction |
| --- | --- | --- |
| Codebase grounding | PASS | Grounded against `skills/code-review/SKILL.md`, `scripts/review/{audit,prompts,rule_matcher}.py`, `tests/test_ocr_language_rules.py`, `rules/AGENTS.md`, and `~/.gemini/config/rules/tdd.md`. |
| Attributable intent and explicit scope | PASS | `REQ-051`..`REQ-054` trace directly to user requests and `ask_question` choices; `Non-goals` preserve `peer_review.py` and forbid file-mutating autofixes. |
| Observable requirements and meaningful acceptance criteria | PASS | Each requirement defines deterministic success and boundary/failure acceptance criteria (`AC-051-1`..`AC-054-2`). |
| Assumptions and owner-deferred questions are explicit | PASS | `peer_review.py` retention assumption recorded; zero unresolved or `[PROVISIONAL]` items. |
| Architectural rationale respects requirements | PASS | `ADR-042` and `ADR-043` deliver fast offline conventions and deterministic linting without breaking `REQ-048` or mutating repos. |
| IDs, references, and revision route are consistent | PASS | Allocates `REQ-051`..`REQ-054` and `ADR-042`..`ADR-043` above prior highest `REQ-050` / `ADR-041` in `docs/specs/INDEX.md`. |
