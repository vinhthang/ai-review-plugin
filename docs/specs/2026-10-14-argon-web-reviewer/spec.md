# Specification: Argon Web Reviewer & Pluggable Engine Architecture

**Feature ID:** `2026-10-14-argon-web-reviewer`  
**Requirement Range:** `REQ-036` to `REQ-040`  
**Status:** In Review (Disambiguated via `/grill-me`)  
**Governing Standard:** [`rules/spec-standard.md`](file:///Users/thanghoang/github/ai-review-plugin/rules/spec-standard.md)  
**Workspace:** `ai-review-plugin`  

---

## 1. Problem Statement & Background

### 1.1 Context
The `ai-review-plugin` currently provides automated adversarial peer reviews across three review modes (`spec`, `design`, `code`). However, the existing implementation suffers from two architectural limitations:
1. **Engine Coupling in Review Orchestration:** In `scripts/review/audit.py` and `scripts/review/engines/__init__.py`, supported engines are hardcoded into CLI choices (`choices=["workbuddy", "codex"]`) and manual `if/elif` branching blocks. Adding a new review engine requires modifying multiple core audit files, violating the Open/Closed Principle.
2. **Missing Web-Based Gemini Reviewer:** External review relies on CLI binaries (`cbc`/`codebuddy` for WorkBuddy and `codex` for OpenAI). Users lack the ability to leverage Gemini web models (such as Gemini Argon with custom instructions/gems like `@software-architect-reviewer`) hosted on Microsoft Edge via browser automation without API token setup.

### 1.2 Objective
Refactor reviewer engine resolution into a pluggable registry and introduce **Argon Web Reviewer** (`--engine argon-web`) as a first-class engine adapter. The adapter automates Microsoft Edge via AppleScript to submit review requests to `gemini.google.com`, stream and extract feedback, and convert responses into canonical `ReviewEnvelope` structured JSON (`review.json`) for automated gating.

---

## 2. Normative Requirements

### `REQ-036`: Pluggable Engine Registry
- **Statement:** The review engine resolution system MUST use a registry pattern (`ENGINE_REGISTRY`) mapping engine identifiers to adapter classes.
- **Acceptance Criteria:**
  - `AC-036.1`: `scripts/review/engines/__init__.py` exposes `register_engine(name, adapter_cls)` and `resolve_engine(cli_engine, session_id)`.
  - `AC-036.2`: Engine names `workbuddy`, `codex`, and `argon-web` are registered cleanly in `ENGINE_REGISTRY`.
  - `AC-036.3`: `scripts/review/audit.py` MUST NOT contain hardcoded `if engine_name == "workbuddy"` or `if engine_name == "codex"` conditional branches for engine instantiation or command resolution.
  - `AC-036.4`: CLI parser in `audit.py` dynamically accepts all registered engine choices without hardcoded lists.

### `REQ-037`: First-Party Edge AppleScript Review Runner
- **Statement:** The Microsoft Edge AppleScript automation script MUST be natively implemented and self-contained in-repo under `scripts/review/runners/edge_applescript_runner.py` (using the scratch prototype strictly as an implementation reference, with zero runtime references or dependencies on external scratch directories). It MUST support both standalone CLI execution and adapter invocation.
- **Acceptance Criteria:**
  - `AC-037.1`: The runner is 100% self-contained in `scripts/review/runners/edge_applescript_runner.py` with zero imports or references to external scratch directories.
  - `AC-037.2`: The runner can be executed as a standalone CLI script: `python3 scripts/review/runners/edge_applescript_runner.py <files...> --out <output_path> [--skill <tag>] [--timeout <sec>]`.
  - `AC-037.3`: When executed without GUI focus, it queries the active Microsoft Edge tab matching `gemini.google.com` via `osascript`, programmatically activating the tab to wake sleeping renderers.
  - `AC-037.4`: It injects prompt content into the input element (`.ql-editor`, `div[contenteditable="true"]`, or `textarea`), triggers the send button, polls generation until complete, and outputs review text to disk.
  - `AC-037.5`: The runner reports actionable error messages distinguishing genuine permission errors from sleeping tab timeouts.
  - `AC-037.6`: The runner eliminates stale response extraction race conditions by tracking the pre-send message count and ensuring new generation has started before entering stability checks.

### `REQ-038`: Argon Web Review Engine Adapter
- **Statement:** An `ArgonWebAdapter` class implementing `ReviewEngineAdapter` MUST be added in `scripts/review/engines/argon.py`.
- **Acceptance Criteria:**
  - `AC-038.1`: `resolve_binary()` discovers `osascript` and locates `edge_applescript_runner.py` (overridable via `ARGON_RUNNER_BIN`).
  - `AC-038.2`: `build_command(...)` packages review prompt, schema requirements, and target paths into runner arguments.
  - `AC-038.3`: Session IDs prefixed with `argon-web:` (e.g. `argon-web:<id>`) bind authoritatively to `ArgonWebAdapter` via dynamic registry session prefix lookup.
  - `AC-038.4`: Default skill mention tag is `@software-architect-reviewer` (configurable via `--model`, `--skill`, or `ARGON_SKILL`).

### `REQ-039`: Hybrid JSON + Markdown Review Envelope Extraction
- **Statement:** `ArgonWebAdapter.extract_review_payload_and_session(...)` MUST implement robust hybrid extraction to produce canonical `ReviewEnvelope` JSON conforming to `schema.json`.
- **Acceptance Criteria:**
  - `AC-039.1`: Searches fenced JSON code blocks (````json ... ````) in reverse order to ensure the reviewer's schema payload is selected over illustrative snippets inside target documents.
  - `AC-039.2`: Strictly bijective severity mapping: `[Critical]`, `[Blocker]`, `[Critical/Blocker]` map to `P0`.
  - `AC-039.3`: Strictly bijective severity mapping: `[Warning]` maps to `P1`.
  - `AC-039.4`: Strictly bijective severity mapping: `[Suggestion]` maps to `P2`.
  - `AC-039.5`: Fail-Closed Fallback: If neither valid JSON nor recognized severity tags exist, the parser MUST abort with an error rather than silently defaulting to an empty issue list (`review_status = "approved"`), unless an explicit positive confirmation sentinel is matched and no refusal/error indicators exist.
  - `AC-039.6`: Output payload is strictly validated and converted into `ReviewEnvelope` with appropriate `review_status` ("approved" when no P0/P1 issues, "rejected" otherwise).

### `REQ-040`: Automated and Live Verification
- **Statement:** The implementation MUST provide both isolated pytest unit test coverage and live end-to-end verification.
- **Acceptance Criteria:**
  - `AC-040.1`: Pytest unit tests in `tests/test_argon_engine.py` verify command building, session resolution, error handling, and hybrid parsing (JSON and Markdown formats) using mock subprocess calls.
  - `AC-040.2`: Existing test suite (`tests/test_peer_review.py`) continues to pass 100% without regression.
  - `AC-040.3`: Live verification test executes `edge_applescript_runner.py` against `docs/specs/2026-10-14-argon-web-reviewer/design.md` and generates `design_review.md`.

---

## 3. Non-Goals & Scope Boundaries
- **Cross-browser support beyond Edge:** Safari, Chrome, and Firefox AppleScript automation are out of scope for this milestone.
- **Multi-turn conversational chat:** Argon Web Reviewer operates as a stateless single-turn review pass; multi-turn prompt negotiation is out of scope.
