# AI Review Plugin: Two-Stage Spec & Plan Review Architecture

The AI Review Plugin implements an autonomous multi-model planning and review protocol aligned with Ray Dalio's 5-Step Process and Superpowers Engineering Philosophy. It enforces a strict **Two-Stage Spec-Driven Development (SDD)** workflow to ensure architectural integrity, prevent regressions, and verify 100% bidirectional traceability before and during code implementation.

---

## Two-Stage Spec & Plan Review Architecture

In complex software projects, conflating architectural design with task implementation plans causes architectural drift, unhandled edge cases, and scope creep. The Two-Stage Review Architecture decouples design from execution:

```
+-----------------------------------------------------------------------------------+
|                        SPEC-DRIVEN DEVELOPMENT WORKFLOW                           |
|                                                                                   |
|  +--------------------+        +---------------------+        +----------------+  |
|  |   BRAINSTORMING    | -----> |     SPEC-REVIEW     | -----> |  PLAN-REVIEW   |  |
|  |  (Set Clear Goals) |        | (Validate WHAT/WHY) |        | (Validate HOW) |  |
|  +--------------------+        +---------------------+        +----------------+  |
|                                           |                           |           |
|                                           v                           v           |
|                                      SPEC APPROVAL               PLAN APPROVAL    |
|                                           |                           |           |
|                                           +---------------------------+           |
|                                                         |                         |
|                                                         v                         |
|                                                    SUBAGENT EXEC                  |
+-----------------------------------------------------------------------------------+
```

1. **Stage 1: Specification Tier (`spec-review`)**:
   - Focus: **WHAT & WHY**. Problem definition, domain boundaries, system topology, interfaces, failure modes, security threat models, and architectural invariants.
   - Prohibits: Granular checklists, task sequencing, file editing operations.
   - Outcome: Approved specification document stored in `docs/superpowers/specs/`.
2. **Stage 2: Implementation Plan Tier (`plan-review` with `SPEC_GATE`)**:
   - Focus: **HOW & SEQUENCE**. Clearly bounded operational implementation tasks formatted as checkboxes (`- [ ]`), explicit file paths, Consumes/Produces interfaces, exact test commands with expected outputs, and minimal diffs.
   - Enforces: Mandatory `SPEC_GATE` verifying bidirectional traceability between the plan and the governing specification (100% spec coverage, zero unapproved scope).

---

## Skills

### 1. `spec-review`
An on-demand skill that performs a rigorous architectural peer review on design specifications in `docs/superpowers/specs/`.
- **Discovery Hierarchy**: Explicit argument `$1` -> Git modified spec (`rtk git status --porcelain docs/superpowers/specs/`) -> newest file in `docs/superpowers/specs/` by `mtime`.
- **Pre-flight Format Validation**: Validates title header, metadata (`Date`, `Status`, `Authors`), required sections (`Context & Motivation`, `Architecture & System Model`, `Component & Interface Contracts`, `Error Handling & Failure Modes`, `Verification & Testing`), absence of `- [ ]` checkboxes, and zero placeholders (`TODO`, `TBD`, `WIP`, ellipsis).
- **Reviewer Invocation**: Dispatches `scripts/peer_review.py --mode spec --target <SPEC_PATH> --repo .`.
- **Ray Dalio's Don't Tolerate Problems**: P0 (critical architectural flaws) and P1 (functional omissions/unhandled failure modes) block execution. P2 issues are non-blocking advisory suggestions.
- **Explicit Human Approval Gate**: Halts at `APPROVAL_GATE` per `rules/explicit-approval.md` before transitioning to implementation planning.

### 2. `plan-review`
An on-demand skill that validates implementation plans and enforces bidirectional alignment with specifications.
- **`SPEC_GATE` Transition**:
  - Reads plan header for `**Spec:** <path>`.
  - Verifies the specification exists on disk.
  - Rejects with diagnostic error if spec is missing or unlinked (unless explicit `--no-spec` override is passed for bounded fixes).
- **Reviewer Invocation**: Dispatches `scripts/peer_review.py --mode plan --target <plan_path> --repo . --spec <resolved_spec_path>` (or `--no-spec`).
- **Escalation Ceiling (ISSUE-R3-01 Fix)**: Enforces `attempt_counter >= 5` or `debate_counter >= 3` escalation to the human user even if a contradictory reviewer payload marks `review_status: "approved"` with P0/P1 issues.
- **Explicit Human Approval Gate**: Halts at `APPROVAL_GATE` per `rules/explicit-approval.md` and `rules/reasoning-quality.md`. Once approved, delegates to `superpowers:subagent-driven-development`.

### 3. `code-review`
The companion code review skill performs a single-pass adversarial review on code changes:
- **Two-Stage Delegation**: Flash subagent generates clean diff; Pro subagent conducts adversarial review (`attention-guard/rules/AGENTS.md`).
- **Environment Safety (ISSUE-R2-01 Fix)**: Protects temporary `GIT_INDEX_FILE` cleanup with POSIX shell trap:
  ```bash
  trap 'unset GIT_INDEX_FILE; rm -f "$GIT_INDEX_FILE"' EXIT
  ```
- **Escalation Ceiling (ISSUE-R3-02 Fix)**: Tracks attempt count and transitions to `ESCALATE` if P0/P1 blockers remain unresolved after 5 attempts.
- **Evidence Preservation (ISSUE-R3-03 Fix)**: Generates and permanently preserves `review.md` in repository root, even when diff is empty.

---

## Engine & CLI Contract (`scripts/peer_review.py`)

The review engine provides deterministic, sandboxed execution using Codex CLI and strict JSON schema output.

### CLI Parameters

```bash
scripts/peer_review.py --target <path> --mode <plan|code|spec> --repo <path> [--spec <path>] [--no-spec] [--message <msg>] [--session-id <id>]
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `--target` | String | Yes | Path to file under review (`spec.md`, `plan.md`, or diff). |
| `--mode` | Enum | Yes | Review mode: `spec`, `plan`, or `code`. |
| `--repo` | String | Yes | Repository root directory to mirror for context. |
| `--spec` | String | Conditional | Path to governing specification file. Required in `--mode plan` unless `--no-spec` is passed. Forbidden in `--mode spec` and `--mode code`. |
| `--no-spec` | Flag | Conditional | Standalone plan review flag without governing specification. Mutually exclusive with `--spec`. Forbidden in `--mode spec` and `--mode code`. |
| `--message` | String | Optional | Follow-up message, fix summary, or technical rebuttal. |
| `--session-id` | String | Optional | Codex thread session ID to resume multi-turn debate. |

### Validation Invariants & Exit Codes

- **Exit Code 0**: Review completed cleanly with zero P0/P1 issues (approved or P2 advisory only).
- **Exit Code 1**: Review completed with one or more P0 or P1 blocking issues.
- **Exit Code 2**: Fatal error:
  - `--spec` and `--no-spec` passed simultaneously (`Fatal: --spec and --no-spec are mutually exclusive.`).
  - `--mode plan` missing both `--spec` and `--no-spec` (`Fatal: --mode plan requires either --spec <path> or --no-spec.`).
  - `--spec` or `--no-spec` passed with `--mode spec` or `--mode code` (`Fatal: --spec cannot be used with --mode <mode>.`).
  - `--spec <path>` points to non-existent file (`Fatal: spec file does not exist: <path>`).
  - Target or repository path does not exist.
  - Codex launch timeout, crash, or corrupted payload.

### Process Safety Controls

- **Graceful SIGKILL (ISSUE-R1-01 Fix)**: Verifies `process.poll() is None` before issuing `SIGKILL` after timeout grace period; never signals reaped processes.
- **PermissionError Guard (ISSUE-R1-02 Fix)**: Catches `(ProcessLookupError, PermissionError)` on all `os.killpg` calls to guard against recycled foreign PIDs.
- **Isolated Session Group (ISSUE-R1-03 Fix)**: Launches child processes with `start_new_session=True` so `os.killpg` targets an isolated session process group without leaking grandchildren.
- **Rsync Fallback (ISSUE-R2-02 Fix)**: If `rsync` is missing or fails in minimal container environments, falls back gracefully to `shutil.copytree` excluding `.git`, `.gemini`, and `AGENTS.md`.

---

## Conceptual Framework: Ray Dalio's 5-Step Process

Plan-Review embodies Ray Dalio's 5-step process for achieving operational excellence:

1. **Set Clear Goals**: Explore user intent, uncover constraints, evaluate trade-offs, and clarify requirements before drafting any plan, seamlessly integrating with `superpowers:brainstorming`.
2. **Identify Problems (Don't Tolerate Problems)**: Surface constraints, breaking changes, and architectural risks early. Never sweep problems under the rug: P0/P1 blockers are never relegated to tech-debt bypass backlogs—P0 issues halt execution and require explicit human resolution.
3. **Diagnose Root Causes**: When a peer review rejects a plan, diagnose the fundamental root cause using `superpowers:systematic-debugging` rather than applying superficial fixes to the plan text.
4. **Design Plans**: Formulate a comprehensive, actionable specification adhering to `superpowers:writing-plans` (clearly bounded operational tasks, exact file paths, explicit interfaces, and concrete test commands).
5. **Push to Results (Execution)**: Enforce an explicit human approval gate per `rules/explicit-approval.md` and `rules/reasoning-quality.md`. Once approved by the user, delegate execution to `superpowers:subagent-driven-development` with continuous verification.

---

## Installation

This plugin **must** be installed into the exact directory path `~/.gemini/config/plugins/ai-review-plugin` for internal paths and skills to resolve correctly across workspaces.
