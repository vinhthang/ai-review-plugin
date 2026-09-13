---
name: plan-review
description: An on-demand skill that implements the Autonomous Multi-Model Planning Protocol aligned with Ray Dalio's 5-Step Process and Superpowers Engineering Philosophy.
---
# Plan-Review Protocol

The `plan-review` skill evaluates an implementation plan against its governing specification, task right-sizing, and TDD rigor. It operationalizes Ray Dalio's 5-Step Process and connects with `superpowers:brainstorming`, `superpowers:writing-plans`, and `superpowers:subagent-driven-development`.

```mermaid
stateDiagram-v2
    [*] --> INIT
    INIT --> DISCOVER
    DISCOVER --> ABORT : Plan File Not Found / Ambiguous
    DISCOVER --> SPEC_GATE : Plan File Resolved
    SPEC_GATE --> ESCALATE : Spec Missing / Invalid / Not Found (without --no-spec)
    SPEC_GATE --> PREPARE : Spec Linked and Valid (or --no-spec Validated)
    PREPARE --> ABORT : Preparation Failure
    PREPARE --> REVIEW : attempt_counter == 0
    PREPARE --> SELF_REVIEW : attempt_counter > 0
    SELF_REVIEW --> REVIEW : Fix is Adequate
    SELF_REVIEW --> DIAGNOSE : Fix is Flawed (self_review_counter < 3)
    SELF_REVIEW --> ESCALATE : Fix is Flawed (self_review_counter >= 3)
    REVIEW --> EVALUATE : Subagent Completed
    REVIEW --> ABORT : Subagent Failed / Launch Error
    EVALUATE --> APPROVAL_GATE : review_status == "approved" or (review_status == "rejected" and no P0/P1 issues)
    EVALUATE --> ESCALATE : attempt_counter >= 5 or debate_counter >= 3
    EVALUATE --> DIAGNOSE : review_status == "rejected" (Agree with P0/P1)
    EVALUATE --> DEBATE : review_status == "rejected" (Disagree with P0/P1)
    EVALUATE --> ABORT : Malformed / Invalid JSON
    DIAGNOSE --> FIX
    FIX --> SELF_REVIEW
    DEBATE --> REVIEW
    ESCALATE --> PREPARE : User Provides Resolution (Reset self_review_counter = 0)
    ESCALATE --> ABORT : User Rejects
    APPROVAL_GATE --> EXECUTE : User Explicitly Approves ("Proceed")
    APPROVAL_GATE --> DIAGNOSE : User Requests Modifications
    APPROVAL_GATE --> ABORT : User Rejects
    EXECUTE --> DONE
    ABORT --> [*]
    DONE --> [*]
```

### State: INIT
**Action:**
- Initialize in-memory loop state:
  `attempt_counter = 0`
  `debate_counter = 0`
  `self_review_counter = 0`
  `session_id = null`
  `resolved_spec_path = null`
- Transition to `DISCOVER`.

### State: DISCOVER
**Action:**
- Connects with `superpowers:brainstorming` (Step 1: Set Clear Goals). Ensure architectural goals were clarified and specifications approved prior to planning.
- Resolve plan target using Plan Resolution Hierarchy:
  1. Priority 1 (Explicit Argument): `$1` if provided.
  2. Priority 2 (Root Implementation Plan): `./implementation_plan.md` in repository root.
  3. Priority 3 (Latest in Archive): Newest file in `docs/superpowers/plans/*.md`.

**Transitions:**
- If plan file resolved -> Transition to `SPEC_GATE`
- If plan file not found or ambiguous -> Transition to `ABORT`

### State: SPEC_GATE (Critical SDD Alignment)
**Action:**
- Enforce the link between Implementation Plan and Specification:
  1. Parse plan file header for the mandatory line: `**Spec:** <path>`.
  2. If `**Spec:** <path>` is present:
     - Resolve `<path>` relative to repository root or canonical path.
     - Verify `<path>` exists on disk and is a valid file.
     - If file does not exist: Emit diagnostic error: `SPEC_GATE FAILURE: Specified spec file does not exist: <path>`. Transition to `ESCALATE`.
     - If file exists: Assign `resolved_spec_path = <path>` for reviewer injection. Transition to `PREPARE`.
  3. If `**Spec:**` header is missing:
     - Check if explicit `--no-spec` override was passed.
     - If `--no-spec` NOT passed: Emit fatal gate error: `SPEC_GATE FAILURE: Plan does not reference a governing spec (**Spec:** header missing). Plans require an approved specification doc, or explicit --no-spec override for bounded fixes.`. Transition to `ESCALATE`.
     - If `--no-spec` IS passed: Verify that the plan describes a small, bounded bugfix or maintenance task. If verified, proceed without spec context.

**Transitions:**
- Gate passed -> Transition to `PREPARE`
- Gate rejected -> Transition to `ESCALATE`

### State: PREPARE
**Action:**
- Upon entering from `ESCALATE` (user resolution), ensure `self_review_counter = 0` is reset to prevent post-escalation deadlocks.
- **Strict Format Standardization**: Adhere strictly to the format defined in `superpowers:writing-plans`:
  - Standard plan header:
    ```markdown
    # [Feature Name] Implementation Plan

    > **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

    **Goal:** [One sentence describing what this builds]
    **Architecture:** [2-3 sentences about approach]
    **Tech Stack:** [Key technologies/libraries]
    **Spec:** [Path to approved spec file, or none (bounded fix)]
    ```
  - Task right-sizing: 2–5 minute bite-sized tasks (`- [ ] Step 1: ...`, etc.).
  - Exact file paths (`Create: exact/path`, `Modify: exact/path:line`, `Test: exact/path`).
  - Explicit interface contracts (Consumes / Produces).
  - Explicit test commands and expected outputs (`Run: rtk pytest ...`, `Expected: PASS`).
  - Concrete code snippets for minimal implementation (zero placeholders, no "TODO", no "TBD").

**Transitions:**
- On failure -> Transition to `ABORT`
- On success and `attempt_counter == 0` -> Transition to `REVIEW`
- On success and `attempt_counter > 0` -> Transition to `SELF_REVIEW`

### State: SELF_REVIEW
**Action:**
- You are acting as a Pre-Reviewer.
- Read the contents of `implementation_plan.md`. Evaluate if the plan revisions address prior findings without regressions.
- Compare the changes against the P0/P1 issues that the Peer Reviewer raised in the previous iteration.
- Increment `self_review_counter`.

**Transitions:**
- If the fix is adequate -> Transition to `REVIEW` (submit to Peer Reviewer)
- If the fix is flawed or incomplete and `self_review_counter < 3` -> Transition to `DIAGNOSE`
- If the fix is flawed or incomplete and `self_review_counter >= 3` -> Transition to `ESCALATE`

### State: REVIEW
**Action:**
- Increment your internal `attempt_counter`.
- Turn 1: Dispatch Peer Reviewer subagent using `scripts/peer_review.py --mode plan --target <plan_path> --repo <repo_path>` along with `--spec <resolved_spec_path>` (if spec exists) or `--no-spec`.
- Pass instructions to evaluate the plan against the `superpowers` rule and return a structured JSON subagent payload:
  ```json
  {
    "status": "completed",
    "review_status": "approved|rejected",
    "summary": "Concise summary of review findings",
    "issues": [
      {
        "severity": "P0|P1|P2",
        "description": "Clear explanation of the architectural or functional flaw"
      }
    ]
  }
  ```
- Turns 2+: Use `send_message` or `--session-id <session_id>` with `--message <rebuttal_or_fix_summary>` to communicate revisions or rebuttals to the Peer Reviewer subagent.
- Set a liveness timer via `schedule` with `TimerCondition: any` (e.g. `DurationSeconds=300`) per `attention-guard/rules/AGENTS.md`.
- Save the subagent's `conversation_id` for subsequent turns.
- Save the full JSON response to `review.json` in the project root directory.

**Transitions:**
- If subagent returns `status == "failed"` -> Transition to `ABORT`
- If subagent returns `status == "completed"` -> Transition to `EVALUATE`

### State: EVALUATE (Step 2: Don't Tolerate Problems)
**Action:**
- Parse and analyze the structured JSON output from `review.json`:
  - P2 issues are non-blocking advisory feedback.
  - P0 issues are critical architectural flaws or security defects.
  - P1 issues are functional bugs, missing requirements, or unhandled edge cases.
- Apply Ray Dalio's Principle: **Don't Tolerate Problems**. Never sweep P0/P1 issues under the rug or relegate them to a backlog. P0 issues must be resolved before proceeding.
- If the outcome is to fix, reset `self_review_counter = 0` and `debate_counter = 0`.
- **P2-Only Guard**: If `review_status == "rejected"` but no P0/P1 issues exist (only P2 advisory issues exist), treat as advisory and transition to `APPROVAL_GATE`.

**Transitions:**
- Priority 1: If `review_status == "approved"` and no P0/P1 issues exist -> Transition to `APPROVAL_GATE`
- Priority 1 (P2-Only Guard): If `review_status == "rejected"` but no P0/P1 issues exist -> Treat as advisory and Transition to `APPROVAL_GATE`
- Priority 2 (Escalation Ceiling - Fix for ISSUE-R3-01): If `attempt_counter >= 5` or `debate_counter >= 3` on any blocking issue -> Transition to `ESCALATE` (even if contradictory `review_status: "approved"` payload contains P0/P1 issues)
- Priority 3: If (`review_status == "rejected"` or P0/P1 issues exist) and you agree with the P0/P1 issues -> Transition to `DIAGNOSE`
- Priority 3: If (`review_status == "rejected"` or P0/P1 issues exist) and you disagree (e.g. out of scope, incorrect, violates requirements) -> Transition to `DEBATE`
- Fail-closed: If `review.json` is missing, malformed, or invalid -> Transition to `ABORT`

### State: DIAGNOSE (Step 3: Diagnose Root Causes)
**Action:**
- Connect with `superpowers:systematic-debugging`.
- Apply the Iron Law: **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST**.
- Diagnose why the plan triggered peer review rejection before modifying any plan text.
- Do not make superficial patches or symptom fixes. Identify the structural root cause (e.g., missed dependency, flawed architectural assumption, incorrect interface boundary).
- Formulate a clear hypothesis and identify the exact structural changes needed.

**Transitions:**
- -> Transition to `FIX`

### State: FIX
**Action:**
- Modify `implementation_plan.md` in-place according to the diagnosed root cause.
- Overwrite `implementation_plan.md` with the updated bite-sized tasks, precise test commands, and interface definitions.

**Transitions:**
- -> Transition to `SELF_REVIEW`

### State: DEBATE
**Action:**
- Do not change the plan text. Formulate a technical rebuttal explaining why the issue is invalid, factually inaccurate, or out of scope.
- Increment `debate_counter`.

**Transitions:**
- -> Transition to `REVIEW` (pass the rebuttal using `send_message`)

### State: ESCALATE (Don't Tolerate Problems - Explicit Human Escalation)
**Action:**
- The review is deadlocked, spec linkage failed, or has reached the 5-attempt limit (`attempt_counter >= 5` or `debate_counter >= 3`).
- **Never bypass blockers**: Do NOT relegate P0/P1 blockers to technical debt backlogs or any bypass mechanism.
- P0 blockers represent critical architectural defects that MUST halt execution and require explicit human resolution.
- STOP execution and present the exact dispute and trade-offs to the human user for decision.

**Transitions:**
- Wait for user input:
  - If User provides resolution or architectural guidance -> Reset `self_review_counter = 0` to prevent post-escalation deadlocks, incorporate user decision into plan, and Transition to `PREPARE`
  - If User Rejects -> Transition to `ABORT`

### State: APPROVAL_GATE (Step 5: Push to Results / Execution Gate)
**Action:**
- Plan is approved by Peer Review (`review_status == "approved"`).
- **Enforce Explicit Approval**: Per `rules/explicit-approval.md` and `rules/reasoning-quality.md`, NEVER automatically execute the plan.
- Present `implementation_plan.md` to the user and request explicit confirmation to execute:
  "Plan approved by peer review. Would you like me to proceed with execution using superpowers:subagent-driven-development?"
- Stop your turn and wait for the user to explicitly greenlight execution ("Proceed", "Execute", or user confirmation).

**Transitions:**
- If User Approves -> Transition to `EXECUTE`
- If User Rejects or requests changes -> Transition to `ABORT` (or `DIAGNOSE`)

### State: EXECUTE (Step 5: Push to Results via Subagents)
**Action:**
- Retain `implementation_plan.md` and `review.json`.
- Delegate execution to `superpowers:subagent-driven-development`.
- Dispatch fresh subagents per task, conduct task-level reviews, and push through each bite-sized step with continuous verification.

**Transitions:**
- -> Transition to `DONE`

### State: DONE
**Action:**
- Terminate any running peer reviewer subagents using `manage_subagents`.
- Preserve `implementation_plan.md`, `review.json`, and verification records.
- Compile final Architecture Decision Record in `docs/adr/` if applicable.

**Transitions:**
- -> Terminal State `[*]`.

### State: ABORT
**Action:**
- Terminate review workflow. Clean up temporary resources and report diagnostic cause to user.

**Transitions:**
- -> Terminal State `[*]`.
