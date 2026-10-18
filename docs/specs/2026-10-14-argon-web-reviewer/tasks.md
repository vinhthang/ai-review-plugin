# Tasks: Argon Web Reviewer & Pluggable Engine Architecture

**Feature ID:** `2026-10-14-argon-web-reviewer`  
**Governing Specification:** [`spec.md`](./spec.md)  
**Status:** Completed (Verified via Automated Pytest Suite)  

---

## Task Checklist & Execution Ledger

### Phase 1: Disambiguation, Specification & Design (REQ-036 to REQ-040)
- [x] Conduct `/grill-me` disambiguation interview resolving 5 architectural branches.
- [x] Author `spec.md` with problem statement and normative requirements `REQ-036`..`REQ-040`.
- [x] Author `decisions.md` containing `ADR-036` through `ADR-040`.
- [x] Author `design.md` with component topology, data flows, and parsing algorithms.
- [x] Author `tasks.md` detailing execution steps.
- [x] Author `verification.md` detailing testing and validation plan.
- [x] Register `2026-10-14-argon-web-reviewer` in `docs/specs/INDEX.md`.

---

### Phase 2: Implementation & Verification

#### Phase 2.1: Pluggable Engine Registry Refactoring (REQ-036)
- [x] Refactor `scripts/review/engines/__init__.py`:
  - [x] Implement `ENGINE_REGISTRY`, `register_engine()`, `get_engine_adapter()`, `get_supported_engines()`.
  - [x] Update `resolve_engine()` to use `get_supported_engines()` and handle prefix `argon-web:`.
- [x] Refactor `scripts/review/audit.py`:
  - [x] Make `--engine` argument accept dynamic choices from `get_supported_engines()`.
  - [x] Replace hardcoded `if/elif` engine instantiation with `get_engine_adapter(engine_name)`.
  - [x] Eliminate engine-specific branching blocks.
- [x] Re-export `ArgonWebAdapter`, `register_engine`, `get_engine_adapter`, `get_supported_engines` in `scripts/peer_review.py`.

#### Phase 2.2: First-Party Edge AppleScript Review Runner (REQ-037)
- [x] Implement `scripts/review/runners/edge_applescript_runner.py`:
  - [x] Implement self-contained runner in `ai-review-plugin` using the scratch prototype strictly as an implementation reference (zero external runtime imports or file references).
  - [x] Add CLI arguments: input files, `--out`, `--skill`, `--timeout`, `--json-prompt`.
  - [x] Support headless DOM execution via `osascript` targeting Microsoft Edge and `gemini.google.com`.
  - [x] Implement stream completion detection and error handling.

#### Phase 2.3: Argon Web Review Engine Adapter (REQ-038, REQ-039)
- [x] Implement `scripts/review/engines/argon.py`:
  - [x] Create `ArgonWebAdapter(ReviewEngineAdapter)`.
  - [x] Implement `resolve_binary()` detecting `osascript` and runner script (with `ARGON_RUNNER_BIN` override support).
  - [x] Implement `build_command(...)` constructing runner execution command.
  - [x] Implement `extract_review_payload_and_session(...)` with hybrid JSON + Markdown parsing.
- [x] Register `ArgonWebAdapter` under `"argon-web"` in `scripts/review/engines/__init__.py`.

#### Phase 2.4: Test Suite & Regression Verification (REQ-040)
- [x] Author `tests/test_argon_engine.py`:
  - [x] Test adapter binary resolution and command construction.
  - [x] Test session prefix handling (`argon-web:<id>`).
  - [x] Test hybrid parser against raw JSON, fenced code blocks, and markdown severity tags.
  - [x] Test error scenarios (missing tab, AppleScript permissions, timeout).
- [x] Run full regression test suite (`rtk pytest`) ensuring 100% of tests pass (124 passed, 0 failed).
