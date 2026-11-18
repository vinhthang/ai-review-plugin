# Tasks: Mechanical Spec-Gate & Traceability Enforcement

**Feature ID:** `2026-10-09-spec-gate-enforcement`  
**Governing Specification:** [`spec.md`](./spec.md)  
**Status:** In-Progress  

---

## Task Checklist & Execution Ledger

### Phase 1: Specification & Design (REQ-031 to REQ-035)
- [x] Author `spec.md` with problem statement (15:20 incident), Mermaid architecture, and normative requirements `REQ-031`..`REQ-035`.
- [x] Author `decisions.md` containing ADR-031 through ADR-034.
- [x] Author `design.md` detailing system topology, hook data contracts, subagent classification heuristics, and AST visitor design.
- [x] Author `tasks.md` defining atomic execution items with requirement citations.
- [x] Author `verification.md` establishing verification strategy, test cases, and verification log.
- [x] Register feature `2026-10-09-spec-gate-enforcement` in `docs/specs/INDEX.md`.

---

### Phase 2: Implementation & Verification

#### Phase 2.1: Specification Verification Engine (REQ-032)
- [x] Create `ai-review-plugin/scripts/spec_checker.py`:
  - [x] Implement `parse_specs_index(index_path)` to extract entries from `docs/specs/INDEX.md`.
  - [x] Implement `get_active_specifications(records)` filtering for `{"Draft", "Planning", "In-Progress", "Approved"}`.
  - [x] Implement `validate_spec_package(package_dir)` verifying existence of `spec.md`, `decisions.md`, `design.md`, and `REQ-xxx` patterns.
  - [x] Implement `verify_active_specification(workspace_root)` returning structured status payload.
  - [x] Implement CLI argument handling (`--workspace`, `--json`, `--quiet`, exit codes 0/1/2).

#### Phase 2.2: Specification Checker Unit Tests (REQ-032)
- [x] Create `ai-review-plugin/tests/test_spec_checker.py`:
  - [x] Test successful verification with valid spec package.
  - [x] Test failure when `INDEX.md` is missing or corrupted.
  - [x] Test failure when active spec package is missing required files (`spec.md`, `decisions.md`, `design.md`).
  - [x] Test CLI invocation with `--workspace` and exit codes.

#### Phase 2.3: Prompt Classification Invariants Update (REQ-034)
- [x] Update `ai-review-plugin/rules/spec-standard.md`:
  - [x] Add explicit mathematical Fast-Path invalidation criteria (`>= 2` code files, any CLI switch, any schema change).
  - [x] Codify invariant that negative execution constraints (*"do not recompile"*) and imperatives specify execution parameters, never Phase 1 exemptions.

#### Phase 2.4: Explicit Approval & Phase Gating Rule Update (REQ-035)
- [x] Update `rules/explicit-approval.md`:
  - [x] Restrict Primary Agent from dispatching mutating subagents before Phase 1 specs exist and human approval ("Proceed") is recorded.
  - [x] Define strict read-only and markdown-restricted planning mode boundary.

#### Phase 2.5: Mechanical PreToolUse Spec-Gate Hook (REQ-031)
- [x] Create `antigravity-attention-guard-plugin/scripts/spec-gate.py`:
  - [x] Read `PreToolUse` JSON payload from stdin.
  - [x] Extract `toolCall` and inspect `Subagents` array.
  - [x] Implement exemption filter (`research`, `translate`, `evaluate`, `refine`, `analyze`).
  - [x] Invoke `spec_checker.py` on gated subagents.
  - [x] Return fail-closed `{"decision": "deny", "reason": "..."}` when no active spec exists.
- [x] Register `spec-gate.py` under `PreToolUse` matcher for `invoke_subagent` in `antigravity-attention-guard-plugin/hooks.json`.
- [x] Add unit tests in `antigravity-attention-guard-plugin/tests/test_spec_gate.py`.

#### Phase 2.6: Continuous AST Traceability Fitness Function (REQ-033)
- [x] Create `ai-review-plugin/tests/test_spec_traceability.py`:
  - [x] Implement `CLIArgumentVisitor` using Python `ast` to detect `add_argument()` in `scripts/*.py`.
  - [x] Implement parser to extract declared CLI flags and requirement IDs (`REQ-xxx`) from `docs/specs/**/spec.md`.
  - [x] Assert 100% of detected CLI arguments are mapped to an active or approved `REQ-xxx`.
  - [x] Verify test catches orphaned CLI flags.

---

### Phase 3: End-to-End Integration & Regression Testing
- [x] Run full test suite in `ai-review-plugin`: `rtk pytest tests/`.
- [x] Run full test suite in `antigravity-attention-guard-plugin`: `rtk pytest tests/`.
- [x] Execute simulation of subagent invocation with and without active spec to confirm mechanical block and pass.
- [x] Update `verification.md` with verbatim test execution logs.
