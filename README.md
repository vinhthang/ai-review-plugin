# Plan-Review: Autonomous Multi-Model Planning & Review Protocol

Plan-Review is an autonomous multi-model planning and review protocol designed to ensure architectural soundness, prevent regressions, and enforce rigorous verification before code implementation begins.

## Conceptual Framework: Ray Dalio's 5-Step Process

Plan-Review embodies Ray Dalio's 5-step process for achieving operational excellence:

1. **Set Clear Goals**: Explore user intent, uncover constraints, evaluate trade-offs, and clarify requirements before drafting any plan, seamlessly integrating with `superpowers:brainstorming`.
2. **Identify Problems (Don't Tolerate Problems)**: Surface constraints, breaking changes, and architectural risks early. Never sweep problems under the rug: P0/P1 blockers are never relegated to tech-debt bypass backlogs—P0 issues halt execution and require explicit human resolution.
3. **Diagnose Root Causes**: When a peer review rejects a plan, diagnose the fundamental root cause using `superpowers:systematic-debugging` rather than applying superficial fixes to the plan text.
4. **Design Plans**: Formulate a comprehensive, actionable specification adhering to `superpowers:writing-plans` (2–5 minute bite-sized tasks, exact file paths, explicit interfaces, and concrete test commands).
5. **Push to Results (Execution)**: Enforce an explicit human approval gate per `rules/explicit-approval.md` and `rules/reasoning-quality.md`. Once approved by the user, delegate execution to `superpowers:subagent-driven-development` with continuous verification.

---

## Installation

This plugin **must** be installed into the exact directory path `~/.gemini/config/plugins/ai-review-plugin` for internal paths and skills to resolve correctly across workspaces.

---

## Architecture & Multi-Model Workflow

Plan-Review separates planning and auditing across two distinct AI models to eliminate blind spots and self-confirmation bias:

```
                  +-------------------------------+
                  |      User / Task Request      |
                  +---------------+---------------+
                                  |
                                  v
                  +-------------------------------+
                  | Step 1: Brainstorming (Goals) |
                  |   (superpowers:brainstorming) |
                  +---------------+---------------+
                                  |
                                  v
                  +-------------------------------+
       +--------->|  Model A: Primary Agent       |<---------+
       |          |  (Step 4: writing-plans)      |          |
       |          +---------------+---------------+          |
       |                          |                          |
       |                          | Writes / Updates         |
       |                          v                          |
       |               implementation_plan.md                |
       |                          |                          |
       |                          | Spawns & Audits          | Rebuttal /
       |                          v                          | Resumed Turn
       |          +-------------------------------+          |
       |          | Model B: Peer Reviewer Subagent|---------+
       |          | (Model: pro / Opus)           |
       |          +---------------+---------------+
       |                          |
       |                          | Emits Structured JSON
       |                          v
       |                    review.json
       |                          |
       |         +----------------+----------------+
       |         |                                 |
       |         v                                 v
       |  (review_status: rejected)       (review_status: approved)
       |         |                                 |
       |  [Step 3: Systematic Debugging]           v
       +--[Diagnose Root Cause & Fix]     +-------------------------------+
                 |                        | Explicit Human Approval Gate  |
           [Deadlock / Att >= 5]          |  (rules/explicit-approval.md) |
                 |                        +---------------+---------------+
                 v                                        |
       +-------------------------------+                  v (User Approves)
       | Step 2: Halt & Escalate       |  +-------------------------------+
       | (Explicit Human Resolution)   |  | Step 5: Execute via Subagents |
       +-------------------------------+  | (subagent-driven-development) |
                                          +-------------------------------+
```

### Components

- **Model A (Primary Agent)**:
  - Conducts goal exploration via `superpowers:brainstorming`.
  - Audits architectural blast radius and edge cases.
  - Drafts and refines `implementation_plan.md` adhering to `superpowers:writing-plans`.
  - Conducts Pre-Review self-checks before dispatching to the reviewer.
  - Manages the peer review lifecycle and structured JSON communication.
  - If rejected, diagnoses the structural root cause via `superpowers:systematic-debugging` before fixing.
  - Upon approval, stops at the **Explicit Human Approval Gate** and awaits user confirmation before executing.

- **Model B (Peer Reviewer Subagent)**:
  - Spawns as an independent `Model: pro` (Opus) subagent.
  - Audits the implementation plan directly against workspace files and specifications.
  - Evaluates architectural blast radius, edge cases, contracts, and testability.
  - Emits a structured JSON payload:
    ```json
    {
      "status": "completed",
      "review_status": "approved|rejected",
      "summary": "Executive summary of review findings",
      "issues": [
        {
          "severity": "P0|P1|P2",
          "description": "Detailed description of the issue"
        }
      ]
    }
    ```
    - **P0 (Critical Blocking)**: Severe architectural flaws, security risks, or breaking contracts. Execution halts.
    - **P1 (Standard Blocking)**: Functional bugs, missing requirements, or significant edge cases. Execution halts.
    - **P2 (Non-Blocking Advice)**: Optimization suggestions, style notes, or minor ergonomics. Does not block execution.

---

## Don't Tolerate Problems (Zero Silent Bypasses)

Plan-Review strictly adheres to Dalio's second principle: **Don't Tolerate Problems**.

- **No Silent Bypasses**: P0 and P1 blocking issues are **never** relegated to technical debt backlogs or bypass folders.
- **Explicit Escalation**: If the review deadlocks or reaches the attempt limit (5 attempts), execution immediately halts. The agent escalates the unresolved blocking issues directly to the human user for explicit determination.
- **Preserved Evidence**: All review artifacts (`review.md`, `review.json`) are preserved as permanent verification evidence and never deleted on success.

---

## Systematic Root Cause Diagnosis

When a peer review rejects a plan, the Primary Agent does not apply superficial edits or engage in guess-and-check thrashing:
- The agent activates `superpowers:systematic-debugging`.
- Follows the Iron Law: **NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST**.
- Diagnoses the structural breakdown (interface mismatch, requirement omission, blast radius conflict).
- Formulates a validated hypothesis and updates the plan text with structural precision.

---

## Standardized Plan Design

Implementation plans generated in `implementation_plan.md` adhere strictly to `superpowers:writing-plans`:
- Standardized header specifying feature goal, architecture, tech stack, and execution sub-skills.
- Bite-sized tasks (2–5 minutes per step).
- Concrete file paths (`Create`, `Modify`, `Test`).
- Explicit interfaces (`Consumes`, `Produces`).
- Test commands and expected output assertions (TDD flow).
- Complete code examples with **zero placeholders** (no "TODO", no "TBD").

---

## Push to Results (Execution)

1. **Human Approval Gate**: In accordance with `rules/explicit-approval.md` and `rules/reasoning-quality.md`, approval by peer review does **not** trigger automatic execution. The agent must present the approved plan to the human partner and await explicit confirmation ("Proceed", "Execute").
2. **Subagent-Driven Execution**: Once the user approves, execution is handed off to `superpowers:subagent-driven-development` to dispatch fresh subagents task-by-task with fresh review checkpoints.

---

## Code Review Skill

The companion `code-review` skill performs a single-pass adversarial review on code changes before finalizing a task:
- **Two-Stage Delegation**: Complying with Attention Guard rules (`attention-guard/rules/AGENTS.md`), terminal commands are never executed directly by the Primary Agent:
  - **Stage 1 (Flash Subagent)**: Generates the clean diff using `rtk git` into `$REVIEW_TARGET`.
  - **Stage 2 (Pro Subagent)**: Performs the adversarial review against the diff and plan context.
- **Clean Git Diffing**: Uses clean conditional inspection with `rtk git` without error suppression:
  ```bash
  if rtk git rev-parse --verify HEAD >/dev/null 2>&1; then rtk git read-tree HEAD; fi
  ```
- **Liveness Tracking**: Spawns subagents with active `schedule` timers (`TimerCondition: any`).
- **Unborn Repository Handling**: Falls back gracefully to Git's empty tree hash (`4b825dc642cb6eb9a060e54bf8d69288fbee4904`) when operating on newly initialized repositories.
- **Evidence Preservation**: `review.md` is preserved in the repository root as durable verification evidence rather than being discarded.
