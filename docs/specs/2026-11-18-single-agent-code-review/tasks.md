# Tasks: Single-agent code-review skill, local scoped linters, and industry coding conventions

Sources: [spec.md](./spec.md), [design.md](./design.md)

## Task 1: Enrich language convention packs, rewrite single-agent `SKILL.md`, and align companion rules

- [x] Complete the work and its applicable checks.
- Covers: REQ-053 / AC-053-1, AC-053-2; REQ-054 / AC-054-1, AC-054-2
- Files: `scripts/review/rules/rule_docs/java.md`, `scripts/review/rules/rule_docs/go.md`, `scripts/review/rules/rule_docs/python.md`, `scripts/review/rules/rule_docs/ts_js_tsx_jsx.md`, `scripts/review/rules/rule_docs/rust.md`, `skills/code-review/SKILL.md`, `rules/AGENTS.md`, `README.md`
- Dependencies: None
- Blocked by: None
- Work: Enrich the 5 core `rule_docs/*.md` files with distilled Google/Effective Java, Google/Uber Go (`*_test.go` enabled), PEP 8 / Google Python, Google TS, and Rust API Guidelines; rewrite `skills/code-review/SKILL.md` for single-agent zero-repo-pollution execution; update `rules/AGENTS.md`, `README.md` (removing stale `< 500` lines note), and `~/.gemini/config/rules/tdd.md`.
- Completion evidence: Verified in [Run 1](./verification.md#run-1--2026-11-18) (`182/182` tests passing, `surface_validator.py` `1707/8000` chars, `agy plugin validate` `0` warnings).

## Task 2: Implement `lint_runner.py` + `prepare_code_review.py` via TDD, symlink Codex skill, and verify suite

- [x] Complete the work and its applicable checks.
- Covers: REQ-051 / AC-051-1, AC-051-2; REQ-052 / AC-052-1, AC-052-2; REQ-054 / AC-054-1
- Files: `skills/code-review/scripts/lint_runner.py`, `skills/code-review/scripts/prepare_code_review.py`, `tests/test_prepare_code_review.py`, `tests/test_skills_conformance.py`, `scripts/spec_checker.py`, `tests/test_spec_checker.py`, `plugin.json`
- Dependencies: Task 1
- Blocked by: None
- Work: Write failing unit tests in `tests/test_prepare_code_review.py` covering uncommitted/staged/`--base`/unborn-HEAD diff extraction, `.git/index` SHA-256 invariance, lockfile filtering, symlinked `~/.codex/skills/code-review` rule resolution, `discover_repo_conventions()`, and `run_scoped_linters()` (`in_diff_hunk`, missing/timeout handling, `--deep-lint` gating); implement `lint_runner.py` and `prepare_code_review.py`; create `~/.codex/skills/code-review` symlink; run `pytest`, `mutation_runner.py` (`>= 80%`), `validate_specs.py`, `surface_validator.py`, `agy plugin validate`, and `quick_validate.py`.
- Completion evidence: Verified in [Run 1](./verification.md#run-1--2026-11-18) (`182/182` tests passing; mutation kill rates `100.0%` on `lint_runner.py` and `94.7%` on `prepare_code_review.py`; Codex symlink dogfooded live).

## Gate 2: traceability and readiness

| Requirement | AC | ADR or rationale | Design | Task | Planned verification | Status / reason |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-051 | AC-051-1 | [Rationale](./decisions.md#architectural-rationale) | [Interfaces](./design.md#interfaces-and-flow) | [Task 2](#task-2-implement-lint_runnerpy--prepare_code_reviewpy-via-tdd-symlink-codex-skill-and-verify-suite) | [AC-051-1](./verification.md#ac-051-1-req-051) | PASS — read-only diff + symlinked rule resolution mapped |
| REQ-051 | AC-051-2 | [Rationale](./decisions.md#architectural-rationale) | [Boundaries](./design.md#boundaries-and-recovery) | [Task 2](#task-2-implement-lint_runnerpy--prepare_code_reviewpy-via-tdd-symlink-codex-skill-and-verify-suite) | [AC-051-2](./verification.md#ac-051-2-req-051) | PASS — empty diff, lockfile skip, and invalid ref cleanup mapped |
| REQ-052 | AC-052-1 | [ADR-043](./decisions.md#adr-043-fast-read-only-cli-linters-by-default-with-opt-in---deep-lint-for-build-tools) | [Interfaces](./design.md#interfaces-and-flow) | [Task 2](#task-2-implement-lint_runnerpy--prepare_code_reviewpy-via-tdd-symlink-codex-skill-and-verify-suite) | [AC-052-1](./verification.md#ac-052-1-req-052) | PASS — repo convention discovery and scoped linters mapped |
| REQ-052 | AC-052-2 | [ADR-043](./decisions.md#adr-043-fast-read-only-cli-linters-by-default-with-opt-in---deep-lint-for-build-tools) | [Boundaries](./design.md#boundaries-and-recovery) | [Task 2](#task-2-implement-lint_runnerpy--prepare_code_reviewpy-via-tdd-symlink-codex-skill-and-verify-suite) | [AC-052-2](./verification.md#ac-052-2-req-052) | PASS — missing binary and timeout resilience mapped |
| REQ-053 | AC-053-1 | [ADR-042](./decisions.md#adr-042-offline-distilled-convention-packs-with-repo-config-precedence-over-live-web-fetching) | [Components](./design.md#components) | [Task 1](#task-1-enrich-language-convention-packs-rewrite-single-agent-skillmd-and-align-companion-rules) | [AC-053-1](./verification.md#ac-053-1-req-053) | PASS — 5 core convention docs and OCR corpus tests mapped |
| REQ-053 | AC-053-2 | [ADR-042](./decisions.md#adr-042-offline-distilled-convention-packs-with-repo-config-precedence-over-live-web-fetching) | [Components](./design.md#components) | [Task 1](#task-1-enrich-language-convention-packs-rewrite-single-agent-skillmd-and-align-companion-rules) | [AC-053-2](./verification.md#ac-053-2-req-053) | PASS — unbundled language fallback lookup guidance mapped |
| REQ-054 | AC-054-1 | [Rationale](./decisions.md#architectural-rationale) | [Components](./design.md#components) | [Task 1](#task-1-enrich-language-convention-packs-rewrite-single-agent-skillmd-and-align-companion-rules), [Task 2](#task-2-implement-lint_runnerpy--prepare_code_reviewpy-via-tdd-symlink-codex-skill-and-verify-suite) | [AC-054-1](./verification.md#ac-054-1-req-054) | PASS — single-agent SKILL.md, rule alignment, and Codex link mapped |
| REQ-054 | AC-054-2 | [Rationale](./decisions.md#architectural-rationale) | [Components](./design.md#components) | [Task 1](#task-1-enrich-language-convention-packs-rewrite-single-agent-skillmd-and-align-companion-rules) | [AC-054-2](./verification.md#ac-054-2-req-054) | PASS — surface_validator 3-skill trigger and budget check mapped |

- Backward scope check: PASS — every modified file and task serves `REQ-051`..`REQ-054`.
- Reference and catalog consistency: PASS — all relative links, `#heading-anchors`, and `docs/specs/INDEX.md` IDs match.
