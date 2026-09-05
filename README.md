# Tribunal: Autonomous Multi-Model Planning Protocol

Tribunal is an autonomous multi-model planning and review protocol designed to ensure architectural soundness, prevent regressions, and enforce rigorous verification before code implementation begins.

## Conceptual Framework: Ray Dalio's 5-Step Process

Tribunal is inspired by Ray Dalio's 5-step process for getting what you want out of life and achieving operational excellence:

1. **Set Clear Goals**: Define the overarching architectural and functional objectives of the task without ambiguity.
2. **Identify Problems**: Surface constraints, potential breakage points, conflicting dependencies, and architectural risks early.
3. **Diagnose Root Causes**: Analyze underlying codebase realities and system trade-offs rather than jumping straight to superficial fixes.
4. **Design Plans**: Formulate a comprehensive, actionable specification (`.tribunal/adr/..._implementation_plan_rev<N>.md`) as an Architecture Decision Record tailored to overcome identified challenges.
5. **Execute Tasks**: Push through the designed plan to completion with systematic verification once consensus is reached.

---

## Architecture & Multi-Model Workflow

Tribunal separates planning and auditing across two distinct AI models to eliminate blind spots and self-confirmation bias:

```
                  +-------------------------+
                  |  User / Task Request    |
                  +------------+------------+
                               |
                               v
                  +-------------------------+
       +--------->|  Model A: Primary Agent |<---------+
       |          |  (Goal & Plan Design)   |          |
       |          +------------+------------+          |
       |                       |                       |
       |                       | Writes/Updates        |
       |                       v                       |
       | .tribunal/adr/*_implementation_plan_rev<N>.md |
       |                       |                       |
Re-plan with                   | Audits (read-only)    | Resume Session
Feedback                       v                       | (Attempt 2..5)
       |          +-------------------------+          |
       |          |  Model B: Codex CLI     |----------+
       |          |  (Adversarial Review)   |
       |          +------------+------------+
       |                       |
       |                       | Emits
       |                       v
       |                 stdout (JSON)
       |                       |
       |        +--------------+--------------+
       |        |                             |
       +--(Rejected / approved: false)        |
                |                             v
                |                   (Approved / approved: true)
         [Attempt >= 5]                       |
                |                             v
                v                 +-------------------------+
        Halt & Escalate           |  Automatic Execution    |
            to User               |  (Model A Implements)   |
                                  +-------------------------+
```

### Components

- **Model A (Primary Agent)**:
  - Explores and contexts the target codebase.
  - Addresses prior blocking issues if review feedback exists.
  - Drafts and iteratively refines plans in `.tribunal/adr/` as Architecture Decision Records.
  - Manages the 1-based attempt counter and session resumption.
  - Captures the JSON from stdout and manually saves it to `.tribunal/adr/` to preserve history.
  - Upon approval, generates a `consensus_summary.md` artifact summarizing the agreed-upon design/code.

- **Model B (Codex CLI Peer Reviewer)**:
  - Runs in a strict `--sandbox read-only` environment, guaranteeing that auditing the codebase cannot cause accidental side-effects, file overwrites, or code mutations.
  - Audits the implementation plan directly against workspace files in `$(pwd)`.
  - Evaluates architectural blast radius, edge cases, and contract compliance.
  - Emits event logs on stdout, errors on stderr, and structured findings to `review.json` containing an `issues` list, where each issue has a `description` and a `severity` classification:
    - **P0 (Critical Blocking)**: Severe architectural flaws, security risks, or guaranteed regressions. Must be fixed before execution.
    - **P1 (Standard Blocking)**: Functional bugs, missing requirements, or significant edge cases. Must be fixed before execution.
    - **P2 (Non-Blocking Advice)**: Optimization suggestions, style improvements, or minor edge cases. Emitted as optional advice and does not block execution.

---

## Session Resumption & Retry Lifecycle (Orchestrator Paradigm)

To enforce robustness and execution boundaries, the core protocol is wrapped in a Python CLI (`scripts/peer_review.py`) combined with the Agent's cognitive loop (The Orchestrator Paradigm).

### 1. Read-Only Sandbox Security
The peer reviewer runs under `--sandbox read-only`. Model B has full read access to inspect the codebase, dependencies, and artifacts, but is strictly disallowed from writing or mutating files. Output is isolated via `review.json` generation.

### 2. Contextual Session Resumption & Orchestrator Paradigm
The Python script (`peer_review.py`) is completely stateless. It does not track attempt counters, create locks, or manage directory persistence across attempts.
- **Agent as Orchestrator**: The AI Agent manages the attempt limits and session resumption in memory.
- **Initial Attempt (`Attempt = 1`)**:
  The script automatically parses the `thread.started` event from Codex's JSONL output and returns the `session_id` in its JSON output to the Agent.
- **Subsequent Attempts (`Attempt > 1`)**:
  The Agent passes `--session-id <SESSION_ID>` to the script, allowing Model B to remember prior critique and verify fixes against previously raised issues.

### 3. Strict Validation & Error Handling
The Python script enforces exact JSON schemas and boundary rules, exiting with specific codes that inform the Primary Agent:
- **Exit 0 (Approved)**: Output is completely valid and contains no P0/P1 blocking issues. The agent proceeds, treating any P2 issues as optional advice.
- **Exit 1 (Rejected)**: Validation passes, but P0/P1 blocking issues exist. The agent increments its attempt and retries.
- **Exit 2 (Fatal Error)**: Codex command fails, or the emitted JSON schema is invalid. Execution halts immediately and is escalated to the user.

---

## Smoke-Test Verification Matrix

| Scenario | Conditions | Expected State Machine Behavior |
| :--- | :--- | :--- |
| **1. First-Pass Approval** | `Attempt = 1`, no P0/P1 issues, exit code 0 | Loop terminates cleanly on Attempt 1. Consensus summary displayed; implementation proceeds automatically. |
| **2. Multi-Turn Rejection & Resumption** | `Attempt = 1` rejected (has P0/P1); UUID extracted; `Attempt = 2` resumed (no P0/P1) | Attempt 1 logs blocking issues. Session `<SESSION_ID>` is stored by the Agent. Attempt 2 resumes session. Plan is approved and executes automatically. |
| **3. 5-Attempt Boundary Escalation** | `Attempt = 1..5` all return P0/P1 issues | Rejections handled for attempts 1–4. Upon Attempt 5 rejection (`Attempt >= 5`), the Agent HALTS immediately and prompts user for direction. No code implementation occurs. |
| **4. Non-Zero CLI Exit / Failure** | Codex crashes or exits with non-zero status | Execution halts closed immediately. Diagnostics logged; no implementation is performed. |
| **5. Malformed JSON / Missing Thread UUID** | `review.json` missing/corrupted or `thread.started` not found | Fail-closed validation triggers. Execution halts without reading stale output or executing code. |

---

## Code Review Skill & The "Empty Tree" Magic Hash

In addition to planning, the Tribunal protocol powers the `code-review` skill, allowing agents to peer-review their own code implementations before completing a task.

Because AI agents often work in entirely empty or newly initialized repositories, traditional Git diff commands (like `git diff HEAD`) will fail with fatal errors. 

To solve this, the `code-review` preparation phase intelligently detects unborn repositories and falls back to:
`git diff 4b825dc642cb6eb9a060e54bf8d69288fbee4904`

This hardcoded SHA-1 string is Git's **empty tree hash** (the mathematical hash of a directory with zero files). By diffing the current staging area against the empty tree, the protocol can generate perfectly formatted, unified diffs showing every file as a newly added file, completely avoiding fatal branch errors and enabling immediate autonomous peer-review in brand-new repositories.
