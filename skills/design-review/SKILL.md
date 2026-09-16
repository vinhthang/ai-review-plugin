---
name: design-review
description: An on-demand skill that implements the Autonomous Multi-Model Planning Protocol aligned with Ray Dalio's 5-Step Process and Superpowers Engineering Philosophy.
---
# Design-Review Protocol

The `design-review` skill evaluates an architectural design document within the 5-File Architecture (`design.md`) against its governing specification (`spec.md`), requirement traceability (`REQ-XXX`), and TDD rigor. It operationalizes Ray Dalio's 5-Step Process using the **Modular Review Architecture** (`docs/superpowers/specs/2026-09-16-modular-review-flows/`).

## Superpowers & Dalio 5-Step Integration
- **Step 1: Set Clear Goals:** Ensure architectural design traces to goals established in `superpowers:brainstorming` and `spec.md`.
- **Step 2: Don't Tolerate Problems:** Rigorously eliminate design flaws; zero tolerance for deferred debt or unaddressed defects.
- **Step 3: Root Cause Diagnosis:** Isolate root causes via `superpowers:systematic-debugging` and `attention-guard/rules/AGENTS.md`.
- **Step 4: Deterministic Design:** Structure implementation plans via `superpowers:writing-plans` with mirrored IDE layouts.
- **Step 5: Execution Accountability:** Delegated execution via `superpowers:subagent-driven-development` strictly gated by `rules/explicit-approval.md` and `rules/reasoning-quality.md`.

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

## Review Execution Lifecycle

### Audit (Read-Only)
1. **Discover Target:** Resolve design target:
   - Explicit argument: `$1` if provided.
   - Active package: `docs/superpowers/specs/<feature-id>/design.md`.
   - Fallback: Newest file in `docs/superpowers/specs/**/design.md` or `docs/superpowers/plans/*.md`.
2. **Spec Precondition Check:** Ensure governing `spec.md` is present and approved. If missing, halt with escalation unless explicitly running with `--no-spec` for standalone plans.
3. **Execute Audit:** Launch an isolated review subagent via `peer_review.py`:
   ```bash
   python3 scripts/peer_review.py --target <resolved_design> --mode design --repo <repo_root> --spec <resolved_spec> --output-file review.json [--prior-review <path>]
   ```
4. **Evaluate Verdict:**
   - **`1. Clean`** (No P0/P1 issues): Transition directly to **Governance**.
   - **`2. Defects Found`** (P0 or P1 issues present): Transition to **Remediation**.
   - **P2-Only Guard:** Advisory findings (P2/P3) do NOT block progression to Governance.
   - **System Error:** Escalate failure immediately. Subagents report structured JSON with `review_status` ("approved" or "rejected").

### Remediation
1. **Issue Triage:** Review each P0/P1 issue. Distinguish accepted defects (`1a`) from disputed feedback (`1b`).
2. **Root Cause Diagnosis (Dalio Step 3):**
   - Dispatch Tier 1 Read-Only Pro Diagnostician (`attention-guard/rules/AGENTS.md`) to isolate root causes with `superpowers:systematic-debugging`.
   - If second failure or ambiguous, dispatch Tier 2 External Second-Opinion (WorkBuddy or Codex).
3. **Stateless Rebuttal Protocol:**
   - For disputed findings, append evidence-backed technical rationale to the prior review context.
   - Do NOT run multi-turn debate loops; inject rebuttal directly into `--prior-review`.
4. **Escalation Ceiling:**
   - If `escalation_counter < 3`: Apply design amendment, mirror to `implementation_plan.md`, and transition back to **Audit** (`3. Re-Audit Loop`) with `--prior-review`.
   - If `escalation_counter >= 3`: Stop autonomous loops and transition directly to **Governance** (`4. Escalated`).

### Governance
1. **Human Gate Presentation:** Present the review verdict and findings dashboard to the user.
2. **User Authorization Gate (`rules/explicit-approval.md`):** Await explicit user action:
   - **`5. Approved` ("Proceed"):** Authorize proceeding to execution (`superpowers:subagent-driven-development`).
   - **`6. Guided Retry`:** User provides direction; reset `escalation_counter = 0`.
   - **`7. Rejected`:** User rejects design.
3. **Audit Ledger Persistence:**
   - Archive the review record to `docs/superpowers/specs/<feature-id>/reviews/design-v<N>.json`.
   - Update feature status and review link in `docs/superpowers/specs/INDEX.md`.
