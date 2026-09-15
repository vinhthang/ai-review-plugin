<rule name="spec-standard">
<description>
Enforces the 3-Document Feature Triad (spec.md, plan.md, tasks.md), the Permanent Infrastructure Layer, the Document Authority Matrix, and the Golden Guardrail under Ray Dalio's 5-Step Process.
</description>

<constraints>
- **The Golden Guardrail**: Do not turn an assumption into a requirement, or an implementation preference into a product constraint.
- **Permanent Infrastructure Layer**:
  - Reusable agent behaviors, security permissions, tool execution rules, and reading order belong exclusively in standing infrastructure (`AGENTS.md`, `rules/*.md`, `skills/`).
  - NEVER create a 4th per-feature markdown file for "agent instructions" (prevents instruction drift).
- **The 3-Document Feature Triad**:
  - **spec.md (WHAT & WHY)**:
    - Scope, problem/outcomes, normative requirements (`REQ-xxx`), acceptance criteria (`AC-xxx`, Given/When/Then), external contracts/schemas, invariants, constraints, and non-goals.
    - Rate of change: **ZERO** during execution (immutable baseline with controlled amendments).
    - MUST NOT contain internal function bodies (> 5 lines), helper algorithms, private class structures, file-by-file edit tasks, or task checkboxes (- [ ]).
  - **plan.md (HOW)**:
    - Engineering architecture, component mapping, data flow, migration strategy, error handling, and trade-offs.
    - Rate of change: **LOW** (amended only upon structural architectural discovery).
    - References spec requirements without duplicating external contracts.
  - **tasks.md (DO & STATE)**:
    - Sequenced operational tasks, state tracking (`- [ ]` -> `- [x]`), explicit requirement references (`Requirements: REQ-xxx`), and task dependencies (`Depends on: T-xxx`).
    - Rate of change: **HIGH** (mutates with test verification evidence).
- **The "Differential Rate of Change" Law**:
  - `plan.md` and `tasks.md` MUST remain separate files. Design decisions and execution state mutate at different rates; combining them introduces state mutation noise into architecture and causes agents to mistake a task for a requirement.
- **Controlled Spec Amendments**:
  - Approval is an immutable baseline with controlled amendments, not a ban on change. If an acceptance criterion is discovered to be impossible, escalate to the human user for explicit re-approval. Never silently redefine requirements in `plan.md`.
- **Optional Lifecycle Bookends**:
  - `research.md`: Pre-flight discovery for complex brownfield code investigation and spikes.
  - `walkthrough.md`: Post-flight verification evidence, test logs, diff summaries, and user handoff.
</constraints>

<instructions>
### 1. Document Authority Matrix
| Concern | Authoritative Location |
| :--- | :--- |
| Security, tool permissions, gating rules | Permanent Infrastructure (`AGENTS.md`, global rules) |
| Observable behavior, business rules, external contracts | `spec.md` |
| Technical architecture, data flow, component design | `plan.md` |
| Work queue, dependencies, verification evidence | `tasks.md` |

*Conflict Invariant*: Any conflict between documents triggers human escalation; never assume "the most recently read document wins."

### 2. Traceability Graph
All engineering work traces forward and backward:
```
spec.md (REQ-xxx) -> plan.md (Design) -> tasks.md (T-xxx -> REQ-xxx) -> code & tests
```
Verification must test against requirements in `spec.md`, not merely match existing implementation code.
</instructions>
</rule>
