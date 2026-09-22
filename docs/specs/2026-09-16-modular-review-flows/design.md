# Design: Modular Review Architecture Refactor

**Feature ID:** `2026-09-16-modular-review-flows`  
**Governing Specification:** [`spec.md`](./spec.md)  
**Status:** Approved

---

## 1. High-Level Lifecycle Architecture

```mermaid
stateDiagram-v2
    [*] --> Audit
    Audit --> Governance : 1. Clean
    Audit --> Remediation : 2. Defects Found

    Remediation --> Audit : 3. Re-Audit Loop
    Remediation --> Governance : 4. Escalated

    Governance --> Done : 5. Approved ("Proceed")
    Governance --> Audit : 6. Guided Retry
    Governance --> [*] : 7. Rejected / Abort
    Done --> [*]
```

### Transition Reference Table:
| Transition | Name | Description |
| :--- | :--- | :--- |
| **`1`** | Clean | Zero P0/P1 issues detected in audit pass. Routes straight to Governance. |
| **`2`** | Defects Found | At least one P0 or P1 issue detected. Triggers Remediation. |
| **`3`** | Re-Audit Loop | Document amended; re-audits via `--prior-review` (`escalation_counter < 3`). |
| **`4`** | Escalated | `escalation_counter >= 3` or diagnosis inconclusive. Routes to Human Gate. |
| **`5`** | Approved | Human approves ("Proceed"). Commits audit ledger and transitions to Phase 2. |
| **`6`** | Guided Retry | Human provides guidance or override. Resets `escalation_counter = 0`. |
| **`7`** | Rejected | Human rejects specification or design. Workflow aborted. |

---

## 2. Separated Stage State Machines

### 2.1 Audit Stage
```mermaid
stateDiagram-v2
    [*] --> ResolveTarget
    ResolveTarget --> RunReviewer : 1. Target Validated
    RunReviewer --> EvaluateFindings : 2. Review Completed

    EvaluateFindings --> Clean : 3a. No Defects
    EvaluateFindings --> Blocked : 3b. P0/P1 Issues
    EvaluateFindings --> Fatal : 3c. System Error

    Clean --> [*]
    Blocked --> [*]
    Fatal --> [*]
```

### 2.2 Remediation Stage
```mermaid
stateDiagram-v2
    [*] --> Triage
    Triage --> Diagnose : 1a. Accept Defect
    Triage --> Rebut : 1b. Dispute Defect

    Diagnose --> Patch : 2a. Fix Isolated
    Rebut --> Patch : 2b. Rebuttal Added

    Patch --> ReAudit : 3a. Under Limit (<3)
    Patch --> Escalate : 3b. Limit Reached (>=3)

    ReAudit --> [*]
    Escalate --> [*]
```

### 2.3 Governance Stage
```mermaid
stateDiagram-v2
    [*] --> Present
    Present --> HumanGate : 1. Dashboard Rendered

    HumanGate --> Archive : 2a. Approve ("Proceed")
    HumanGate --> Retry : 2b. Guidance (Reset counter)
    HumanGate --> Abort : 2c. Reject Specification

    Archive --> Done : 3. Ledger Committed
    Done --> [*]
    Retry --> [*]
    Abort --> [*]
```
