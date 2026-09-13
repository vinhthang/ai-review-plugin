# Attention Guard Alignment with Ray Dalio's 5-Step Process Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the Attention Guard plugin's rules, schemas, command security, and deployment automation with Ray Dalio's 5-Step Process and Superpowers engineering principles—eliminating over-engineering in favor of clean, robust, and maintainable architecture.
**Architecture:** 3 Draft-07 JSON schemas in `schemas/`, direct-argv command security in `scripts/command_validator.py` with P0 path confinement, standalone payload validator in `scripts/payload_validator.py`, updated core rules in `rules/`, verified deployment script in `scripts/deploy_plugin.py`, and comprehensive behavioral tests in `tests/test_dalio_conformance.py`.
**Tech Stack:** Python 3.10+, jsonschema (Draft7Validator, FormatChecker), pytest, shlex, ast, rtk, bash.
**Spec:** docs/superpowers/specs/2026-09-13-attention-guard-dalio-alignment-specification.md

---

## Proposed Changes

### Component 1: Role JSON Schemas (`schemas/`)

We introduce 3 formal Draft-07 JSON Schemas with `additionalProperties: false` in `/Users/thanghoang/github/antigravity-attention-guard-plugin/schemas/`.

#### [NEW] [diagnostician-payload.json](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/schemas/diagnostician-payload.json)
- Draft-07 schema for Diagnostician (`pro`), requiring `execution_attempt_id` (UUID), `status` (`completed|failed`), `summary` (10-1200 chars), and conditional `diagnosis`.
- When `status == "completed"`: `diagnosis` is required with `root_cause_status` (`determined|inconclusive`), `proximate_cause`, `evidence` array, and `remediation_plan`.
- If `root_cause_status == "determined"`: `root_cause` required.
- If `root_cause_status == "inconclusive"`: `competing_hypotheses` required.

#### [NEW] [executor-payload.json](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/schemas/executor-payload.json)
- Draft-07 schema for Executor (`flash`), requiring `execution_attempt_id` (UUID), `status` (`completed|failed`), `summary` (10-1200 chars).
- When `status == "completed"`: requires `files_modified` array, `test_results` object (`passed`, `failed == 0`, `total`, `command_executed`), forbids `error_details`.
- When `status == "failed"`: requires `error_details` with `failure_kind` (enum: `SHELL_NON_ZERO_EXIT`, `PAYLOAD_SCHEMA_VIOLATION`, `COMMAND_POLICY_VIOLATION`, `LIVENESS_TIMEOUT`, `SYSTEM_SIGNAL`, `ASSERTION_FAILURE`), and `diagnostic_message`.

#### [NEW] [coordinator-payload.json](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/schemas/coordinator-payload.json)
- Draft-07 schema for Coordinator (`pro`), requiring `execution_attempt_id` (UUID), `status`, `summary`, and `subagent_results` array.
- Failure Propagation Invariant: If any child result has `status: "failed"` without `advisory: true`, top-level status must be `"failed"`.

---

### Component 2: Command Security & Validator (`scripts/command_validator.py`)

#### [NEW] [command_validator.py](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/scripts/command_validator.py)
- Direct `argv` validation using `shlex.split()`.
- Unwraps `rtk` prefix recursively.
- Enforces binary whitelist: `rtk`, `pytest`, `python3`, `python`, `git`, `rsync`.
- Rejects shell operators: pipes `|`, redirects `>`, `>>`, `<`; subshells `sh -c`, `bash -c`; `eval`; backticks.
- Git subcommand policy: only allow `status`, `diff`, `log`, `add`, `commit`. Forbids `-C`, `--git-dir`, `--work-tree`, `--exec-path`.
- Python script policy: script argument must exist, end in `.py`, and reside within `workspace_root` (or deployment script).
- Path confinement policy:
  - Positional paths must reside within `workspace_root`.
  - **P0 Fix**: Only allow paths in `~/.gemini/config/plugins` IF binary is `python3` and script is `scripts/deploy_plugin.py`.
  - Cross-repo read exception: allow `/Users/thanghoang/github/ai-review-plugin/tests/` when binary is `pytest`.

---

### Component 3: Standalone Payload Validator (`scripts/payload_validator.py`)

#### [NEW] [payload_validator.py](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/scripts/payload_validator.py)
- Standalone utility providing `validate_payload(role: str, payload: dict) -> Tuple[bool, Optional[str]]`.
- Resolves schemas from `../schemas/{role}-payload.json`.
- Enforces `jsonschema.Draft7Validator` with `jsonschema.FormatChecker` (validating UUIDs).
- CLI entrypoint: `python3 scripts/payload_validator.py --role <role> --file <path>`.

---

### Component 4: Core Agent Rules (`rules/`)

#### [MODIFY] [AGENTS.md](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/rules/AGENTS.md)
- Codify Ray Dalio's 5-Step Process into the Primary Agent cognitive loop:
  - Step 1 (Clear Goals): Phase 1 defines falsifiable acceptance criteria (automated test commands & exit criteria).
  - Step 2 (Problem Intolerance): Zero error suppression. Failures are structural blockers.
  - Step 3 (Root Cause Diagnosis): Strictly read-only diagnosis gate (`pro` model) separating proximate vs. root causes before any plan modifications. Max 3 escalations before explicit human escalation.
  - Step 4 (Deterministic Design): Implementation plans gated by unbreachable human approval.
  - Step 5 (Execution Accountability): Dispatches executors with unique `execution_attempt_id` and strict JSON payloads.
  - Liveness timer lifecycle (300s, `TimerCondition: any`).

#### [MODIFY] [EXECUTOR.md](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/rules/EXECUTOR.md)
- Mechanical execution, zero delegation.
- Immediate halting invariant on command or assertion failure.
- Strict 1200-character summary limit.
- Structured JSON response complying with `schemas/executor-payload.json`.

#### [MODIFY] [COORDINATOR.md](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/rules/COORDINATOR.md)
- Maximum recursion depth: 1.
- Sequential mutators (code changers), parallel readers (researchers).
- Lossless telemetry aggregation into `subagent_results`.
- Mandatory failure propagation if any non-advisory child fails.

---

### Component 5: Verified Plugin Deployment Script (`scripts/deploy_plugin.py`)

#### [NEW] [deploy_plugin.py](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/scripts/deploy_plugin.py)
- Clean, robust deployment script:
  - Runs pre-flight verification: asserts all 5 bundle items exist in source (`plugin.json`, `hooks.json`, `rules/`, `schemas/`, `scripts/`).
  - Verifies target `~/.gemini/config/plugins/attention-guard`:
    - If target is a symlink, ensures it points to the canonical repo directory.
    - If target is a directory, copies bundle cleanly and idempotently.
  - CLI options: `--verify-only` and `--deploy`.

---

### Component 6: Behavioral Conformance Test Suite (`tests/test_dalio_conformance.py`)

#### [NEW] [test_dalio_conformance.py](file:///Users/thanghoang/github/antigravity-attention-guard-plugin/tests/test_dalio_conformance.py)
- Comprehensive test suite covering:
  - `test_diagnostician_schema_valid_and_invalid`: tests determined, inconclusive, missing root cause, and invalid UUID.
  - `test_executor_schema_valid_and_invalid`: tests success payload, failure payload across failure kinds, error_details rejection on success.
  - `test_coordinator_failure_propagation`: verifies failed child forces coordinator failure.
  - `test_command_validator_whitelist_and_syntax`: verifies dangerous commands (`eval`, `rm -rf`, pipes) are rejected.
  - `test_command_validator_path_confinement`: tests traversal rejection, cross-repo pytest exception, and deploy script exception.
  - `test_ast_no_error_suppression`: parses all scripts with Python `ast` and asserts 0 bare `pass` in `ast.ExceptHandler`.
  - `test_deploy_plugin_verification`: tests bundle verification and deployment safety.

---

## Sequential Implementation Tasks

- [ ] **Task 1: Role JSON Schemas**
  - Create `schemas/diagnostician-payload.json`, `schemas/executor-payload.json`, and `schemas/coordinator-payload.json` in `/Users/thanghoang/github/antigravity-attention-guard-plugin`.
  - Verify JSON syntax validity with `python3 -m json.tool`.

- [ ] **Task 2: Payload Validator**
  - Implement `scripts/payload_validator.py` with Draft7Validator and FormatChecker.
  - Unit test against schemas using sample valid and invalid payloads.

- [ ] **Task 3: Command Security Validator with P0 Fix**
  - Implement `scripts/command_validator.py` with shlex parsing, binary whitelist, git subcommand whitelist, workspace confinement, and P0 deploy path exception.

- [ ] **Task 4: Core Agent Rules Update**
  - Overwrite `rules/AGENTS.md`, `rules/EXECUTOR.md`, and `rules/COORDINATOR.md` with complete, Dalio-aligned rules.

- [ ] **Task 5: Verified Deployment Script**
  - Implement `scripts/deploy_plugin.py` verifying the 5 bundle items and updating `~/.gemini/config/plugins/attention-guard`.

- [ ] **Task 6: Comprehensive Behavioral Test Suite & Verification**
  - Implement `tests/test_dalio_conformance.py`.
  - Execute Attention Guard tests: `rtk pytest /Users/thanghoang/github/antigravity-attention-guard-plugin/tests/test_dalio_conformance.py -v`.
  - Execute AI Review Plugin regression tests: `rtk pytest /Users/thanghoang/github/ai-review-plugin/tests/test_peer_review.py /Users/thanghoang/github/ai-review-plugin/tests/test_skills_conformance.py -v`.
  - Run deployment script: `python3 /Users/thanghoang/github/antigravity-attention-guard-plugin/scripts/deploy_plugin.py --deploy`.
