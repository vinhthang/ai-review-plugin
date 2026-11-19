# Single-agent code-review skill, local scoped linters, and industry coding conventions

- Feature ID: 2026-11-18-single-agent-code-review
- Type: enhancement
- Status: In-Testing
- First entered In-Testing: 2026-11-18
- Related specifications: Implemented: Changes [2026-10-20-harness2-sandbox-and-inv-dom-review](../2026-10-20-harness2-sandbox-and-inv-dom-review/spec.md), [2026-10-30-ocr-language-rules-integration](../2026-10-30-ocr-language-rules-integration/spec.md)

## Problem and source intent

User requests:
1. "review the skill code-review, I want to use code-review, but no need to call other agent"
2. "I aso want to use an out side, general well known coding convention, like for when review java code, the review process will find that coding convention and use it, and thing like java lint, same for review golang, what do you think"

Grounding against `skills/code-review/SKILL.md`, `scripts/review/{audit,prompts,rule_matcher}.py`, `rules/AGENTS.md`, and `~/.gemini/config/rules/tdd.md` exposed four defects:
1. `skills/code-review/SKILL.md` spawns two `invoke_subagent` workers plus an external `peer_review.py` engine subprocess (and omits required `--target` on line 70), turning every code review into a multi-agent run instead of an immediate single-agent review.
2. `skills/code-review/SKILL.md` writes `review.md`, `review.json`, `.code-review/`, and `docs/adr/YYYYMMDD_HHMM_*.md` into the target repository, dirtying `git status` and violating zero-repo-pollution rules.
3. `scripts/review/rules/rule_docs/go.md` tells reviewers not to duplicate `gofmt`/`go vet`/`staticcheck` while never running local linters and still marks `*_test.go` as excluded on line 67; meanwhile `java.md`, `go.md`, `python.md`, `ts_js_tsx_jsx.md`, and `rust.md` lack explicit Google / Effective Java / Uber Go / PEP 8 / Rust API convention sections.
4. `ai-review-plugin/rules/AGENTS.md` and `~/.gemini/config/rules/tdd.md` still mandate multi-engine sandbox reviews or separate reviewer agents for `code-review`, and `~/.codex/skills/code-review` is not linked for OpenAI Codex portability.

## Repository grounding

- `skills/code-review/SKILL.md`: 132-line multi-subagent workflow calling `scripts/peer_review.py` and writing `review.md` and `docs/adr/`.
- `scripts/review/rule_matcher.py` & `scripts/review/rules/`: `system_rules.json` (58 globs) and 57 `rule_docs/*.md` checklists enforced by `tests/test_ocr_language_rules.py` (`len(md_files) == 57`, `"Go Review Principles"` in `go.md`, `"Mutable Default Arguments"` in `python.md`).
- `rules/AGENTS.md`: Always-on governance rule validated by `surface_validator.py` (`REQ-047`).
- `README.md`: Documents `spec-review`, `design-review`, `code-review`, and `scripts/peer_review.py` (including a stale `< 500` lines note on line 74).

## Non-goals

- Removing `scripts/peer_review.py`, `spec-review`, or `design-review` engine adapters (`WorkBuddyAdapter`, `CodexAdapter`, `ArgonWebAdapter`).
- Auto-formatting or mutating repository files (`gofmt -w`, `ruff --fix`, `eslint --fix`) during `code-review`.

## Requirements

### REQ-051: Read-only diff and language-rule collector (`prepare_code_review.py`)

- Current contract: Changed by [2026-11-18-mobile-kotlin-swift-code-review/REQ-055](../2026-11-18-mobile-kotlin-swift-code-review/spec.md#req-055-mobile-lockfile-filtering-for-swift-and-kotlingradle-prepare_code_reviewpy)
- Source intent: User request ("I want to use code-review, but no need to call other agent") and selected pure single-agent collector option.
- Statement: WHEN `prepare_code_review.py` is invoked against a git repository (default uncommitted + untracked, `--staged`, `--base <ref>`, or `--diff-file <path>`), THE script SHALL capture the unified diff using an isolated temporary `GIT_INDEX_FILE`, skip lockfile bodies while recording skipped lockfiles, resolve deduplicated `<language_review_rules>` via `scripts/review/rule_matcher.py` (including when invoked via symlink at `~/.codex/skills/code-review`), and leave `.git/index` and the working tree byte-identical.
- AC-051-1 — Success: Running `prepare_code_review.py` on a repo with staged, unstaged, and untracked `.py`/`.java`/`.go` changes outputs `empty_diff: false`, changed paths, matched `python.md`/`java.md`/`go.md` checklists, and unified diff text while keeping `.git/index` SHA-256 and `git status --porcelain` unchanged (including from a symlinked skill path and on unborn `HEAD` repos).
- AC-051-2 — Boundary/failure: IF the diff is empty, touches lockfiles (`package-lock.json`, `Cargo.lock`, `uv.lock`), or targets a non-git directory / invalid `--base` ref, THEN `prepare_code_review.py` SHALL report `empty_diff: true` cleanly on empty diffs, omit lockfile hunks while listing them in `skipped_lockfiles`, and exit non-zero with a clear diagnostic on invalid repositories or refs without leaving temporary index files behind.

### REQ-052: Repo convention auto-discovery and fast read-only scoped linters (`lint_runner.py`)

- Current contract: Changed by [2026-11-18-mobile-kotlin-swift-code-review/REQ-056](../2026-11-18-mobile-kotlin-swift-code-review/spec.md#req-056-swift-and-kotlinandroid-convention-discovery-and-read-only-scoped-linters-lint_runnerpy--skillmd)
- Source intent: User request ("find that coding convention and use it, and thing like java lint, same for review golang") and selected fast read-only CLI linter + repo-config discovery option.
- Statement: WHEN `prepare_code_review.py` runs without `--no-lint`, THE `lint_runner.py` module SHALL discover repository-level style/linter configs (including `go.mod` Go version, `.golangci.yml`, `checkstyle.xml`, `pmd.xml`, `pyproject.toml`, `.editorconfig`, `CONTRIBUTING.md`), execute `git diff --check` and installed fast read-only CLI linters (`gofmt -l`, `go vet`, `golangci-lint`/`staticcheck`, `checkstyle`, `pmd`, `ruff`, `rustfmt --check`, `shellcheck`, `biome`/`eslint`, `actionlint`) scoped to changed files/packages, tag findings inside changed hunks (`in_diff_hunk`), skip missing binaries without error, and gate slow build-tool linters (`mvn`/`gradle`, `cargo clippy`) behind `--deep-lint`.
- AC-052-1 — Success: `discover_repo_conventions()` identifies repo config files and `go.mod` `go 1.XX` version, and `run_scoped_linters()` captures diagnostics from `git diff --check` and available/stubbed CLI linters on `PATH` with accurate `in_diff_hunk` tagging while gating build-tool linters behind `--deep-lint`.
- AC-052-2 — Boundary/failure: IF a linter binary is absent from `PATH` or exceeds `timeout_sec`, THEN `run_scoped_linters()` SHALL record the skip/timeout in metadata and return partial results without raising unhandled exceptions or mutating repository files.

### REQ-053: Distilled industry coding conventions across core `rule_docs/*.md`

- Current contract: Changed by [2026-11-18-mobile-kotlin-swift-code-review/REQ-057](../2026-11-18-mobile-kotlin-swift-code-review/spec.md#req-057-distilled-kotlin-android--coroutines--compose-and-swift-api-design--swift-testing-convention-packs)
- Source intent: User request for well-known outside coding conventions (Java, Go, etc.) and selected offline distilled standards option.
- Statement: WHEN `rule_matcher.py` resolves checklists from `scripts/review/rules/rule_docs/`, THE corpus SHALL maintain all 57 `rule_docs/*.md` files while enriching `java.md` (Google Java Style + Effective Java 3e + Java 17/21 idioms alongside Axon's 5 Spring Boot test-hygiene rules), `go.md` (Google Go + Uber Go Style + Effective Go and active `*_test.go` test review), `python.md` (PEP 8 + Google Python Style), `ts_js_tsx_jsx.md` (Google TypeScript Style), and `rust.md` (Rust API Guidelines).
- AC-053-1 — Success: `java.md`, `go.md`, `python.md`, `ts_js_tsx_jsx.md`, and `rust.md` contain their distilled convention sections; `go.md` reviews `*_test.go` table tests/`t.Helper()`/goroutine `t.Fatal` misuse instead of claiming `*_test.go` is excluded; and all `tests/test_ocr_language_rules.py` checks (`57` rule docs, `58` globs, heading markers) pass.
- AC-053-2 — Boundary/failure: IF a reviewed file belongs to an unbundled language/framework lacking convention coverage (`default.md` fallback), THEN `skills/code-review/SKILL.md` SHALL permit targeted web/doc lookup only on demand rather than fetching external style guides when bundled rules already match.

### REQ-054: Single-agent `SKILL.md`, zero-repo-pollution reporting, and companion rule alignment

- Current contract: Changed by [2026-11-18-mobile-kotlin-swift-code-review/REQ-056](../2026-11-18-mobile-kotlin-swift-code-review/spec.md#req-056-swift-and-kotlinandroid-convention-discovery-and-read-only-scoped-linters-lint_runnerpy--skillmd)
- Source intent: User selections to execute `code-review` with zero subagents/external calls, report in chat with zero repo files, and align `ai-review-plugin/rules/AGENTS.md` + `~/.gemini/config/rules/tdd.md` + Codex symlink.
- Statement: WHEN an agent invokes `code-review`, THE `skills/code-review/SKILL.md` instructions SHALL run `prepare_code_review.py` directly, apply convention precedence (`repo_conventions` -> `linter_findings` -> `<language_review_rules>` -> on-demand lookup), verify surrounding context (`Ground A`/`Ground B`), and report `P0`/`P1`/`P2` findings in chat without spawning subagents/external engines or writing files into the repository; and `ai-review-plugin/rules/AGENTS.md`, `README.md`, `~/.gemini/config/rules/tdd.md`, and `~/.codex/skills/code-review` SHALL align with this contract.
- AC-054-1 — Success: `skills/code-review/SKILL.md` contains zero `invoke_subagent`, `schedule`, `peer_review.py`, `review.md` write, or `docs/adr/` creation directives; `~/.codex/skills/code-review` resolves to `skills/code-review`; `ai-review-plugin/rules/AGENTS.md` and `~/.gemini/config/rules/tdd.md` permit direct single-agent `code-review`; and `surface_validator.py`, `agy plugin validate`, and `quick_validate.py` exit `0`.
- AC-054-2 — Boundary/failure: IF `ai-review-plugin/rules/AGENTS.md` drops any of its 3 skill triggers (`spec-review`, `design-review`, `code-review`) or exceeds the `8,000`-character always-on budget, THEN `surface_validator.py` SHALL fail validation.

## Assumptions and owner-deferred questions

- Reversible assumption: Keeping `scripts/peer_review.py` and its existing test modules intact preserves `spec-review` and `design-review` compatibility while decoupling `code-review` completely from external engines.

## Approvals and lifecycle history

- 2026-11-18 (`Planning -> In-Progress`): User approved `implementation_plan.md` covering single-agent `code-review`, local scoped linters, distilled industry conventions, zero repo pollution, and companion rule updates.
- 2026-11-18 (`In-Progress -> In-Testing`): Tasks 1 and 2 completed (`182/182` unit tests, `100.0%` and `94.7%` mutation kill rates, `~/.codex/skills/code-review` live); recorded [Run 1](./verification.md#run-1--2026-11-18).
