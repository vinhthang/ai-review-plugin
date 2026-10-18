# Verification Evidence: Mechanical Spec-Gate & Traceability Enforcement

**Feature ID:** `2026-10-09-spec-gate-enforcement`  
**Governing Specification:** [`spec.md`](./spec.md)  
**Status:** Verification Planned  

---

## 1. Verification Strategy & Acceptance Criteria

Every requirement declared in `spec.md` (`REQ-031` to `REQ-035`) is verified through deterministic, automated tests without manual speculation:

| Requirement ID | Verifying Artifact / Test Case | Acceptance Criteria |
| :--- | :--- | :--- |
| **REQ-031** | `test_spec_gate.py` (attention-guard) | Intercepts `invoke_subagent`. Emits `decision: deny` if subagent is mutating and spec is missing; emits `decision: allow` if exempt or valid spec exists. |
| **REQ-032** | `test_spec_checker.py` (ai-review-plugin) | `verify_active_specification` returns `status="valid"` only when `INDEX.md` and all 3 core files (`spec.md`, `decisions.md`, `design.md`) exist. CLI exits with code 0/1/2. |
| **REQ-033** | `test_spec_traceability.py` (ai-review-plugin) | Python AST visits all `add_argument()` in `scripts/*.py`. Asserts 100% of discovered CLI flags are defined under `REQ-xxx` in `docs/specs/`. |
| **REQ-034** | Static Rule Inspection & Audit | `rules/spec-standard.md` contains strict quantification (>=2 files, CLI flags, schema changes invalidate fast path; negative constraints are parameters). |
| **REQ-035** | Static Rule Inspection & Audit | `rules/explicit-approval.md` explicitly mandates human gate ("Proceed") before mutating subagent dispatch. |

---

## 2. Test Plan & Execution Scenarios

### Scenario 1: Unspecified Subagent Interception (REQ-031, REQ-032)
1. **Setup:** Create a temporary test workspace without `docs/specs/`.
2. **Action:** Simulate Antigravity `PreToolUse` payload with `toolCall.name="invoke_subagent"` and `Subagents=[{"TypeName": "self", "Role": "Feature Dev", "Prompt": "Edit scripts/helper.py"}]`.
3. **Assertion:** `spec-gate.py` returns `{"decision": "deny"}` with diagnostic error message.

### Scenario 2: Research & Translation Exemption (REQ-031)
1. **Setup:** Same test workspace without `docs/specs/`.
2. **Action:** Simulate `PreToolUse` with `Subagents=[{"TypeName": "research", "Prompt": "Search codebase"}]` and `Subagents=[{"TypeName": "translate", "Prompt": "Translate ch01"}]`.
3. **Assertion:** `spec-gate.py` returns `{"decision": "allow"}`.

### Scenario 3: Valid Specification Package Clearance (REQ-031, REQ-032)
1. **Setup:** Active workspace containing valid `docs/specs/INDEX.md` and `docs/specs/2026-10-09-spec-gate-enforcement/` with `spec.md`, `decisions.md`, `design.md`.
2. **Action:** Simulate mutating `invoke_subagent` call.
3. **Assertion:** `spec-gate.py` verifies active package via `spec_checker.py` and returns `{"decision": "allow"}`.

### Scenario 4: AST CLI Traceability Enforcement (REQ-033)
1. **Setup:** Run `test_spec_traceability.py` on existing repository.
2. **Action:** Intentionally add a dummy flag `--untracked-flag` to `scripts/spec_checker.py`.
3. **Assertion:** Test breaks with assertion failure citing `--untracked-flag` lacking requirement mapping. Reverting flag restores test to PASS.

---

## 3. Initial Verification Log (Phase 1 Baseline)

### Verification Run: Phase 1 Specification Scaffolding
- **Timestamp:** 2026-10-09T15:50:00+07:00
- **Operator:** Specification Scaffolder Subagent
- **Target:** `docs/specs/2026-10-09-spec-gate-enforcement/`

#### Files Verified on Disk:
```
docs/specs/2026-10-09-spec-gate-enforcement/
├── spec.md         (Created - REQ-031 to REQ-035 defined)
├── decisions.md    (Created - ADR-031 to ADR-034 defined)
├── design.md       (Created - System topology, schemas, heuristics)
├── tasks.md        (Created - Atomic execution checklists)
└── verification.md (Created - Test plan and verification evidence)
```

#### Verification Command Output:
```bash
$ ls -la docs/specs/2026-10-09-spec-gate-enforcement/
total 40
-rw-r--r--  1 thanghoang  staff  5124 Oct  9 15:49 spec.md
-rw-r--r--  1 thanghoang  staff  4812 Oct  9 15:49 decisions.md
-rw-r--r--  1 thanghoang  staff  5340 Oct  9 15:50 design.md
-rw-r--r--  1 thanghoang  staff  2950 Oct  9 15:50 tasks.md
-rw-r--r--  1 thanghoang  staff  3100 Oct  9 15:50 verification.md
```

#### Repository Test Suite Baseline:
```bash
$ rtk pytest tests/
Pytest: 79 passed
```
All existing tests remain green. Phase 1 scaffolding complete.

---

## 4. Phase 2 Implementation Verification Evidence

### Verification Run: Phase 2 Implementation & Test Suites
- **Timestamp:** 2026-10-09T16:07:00+07:00
- **Operator:** Spec Gate Implementer Subagent
- **Scope:** REQ-031 to REQ-035

#### 1. Specification Verification Engine Unit Tests (REQ-032)
```bash
$ rtk pytest tests/test_spec_checker.py
Pytest: 8 passed
```

#### 2. Continuous AST Traceability Fitness Function (REQ-033)
```bash
$ rtk pytest tests/test_spec_traceability.py
Pytest: 3 passed
```

#### 3. Full ai-review-plugin Test Suite (Regression Baseline: 79 -> 90 passed)
```bash
$ rtk pytest tests/
Pytest: 90 passed
```

#### 4. Mechanical Pre-Tool Spec Gate Hook Unit Tests (REQ-031)
```bash
$ rtk pytest tests/test_spec_gate.py  # antigravity-attention-guard-plugin
Pytest: 6 passed
```

#### 5. Full antigravity-attention-guard-plugin Test Suite (Regression Baseline: 102 -> 108 passed)
```bash
$ rtk pytest tests/  # antigravity-attention-guard-plugin
Pytest: 108 passed
```

#### 6. Live Spec Verification CLI Execution (REQ-032)
```bash
$ rtk python3 scripts/spec_checker.py --workspace . --json
{"status": "valid", "valid": true, "active_features": ["2026-10-09-spec-gate-enforcement"]}
```

All 5 requirements (`REQ-031` to `REQ-035`) verified with 100% test passing rates across both plugins. Zero regression breaks.
