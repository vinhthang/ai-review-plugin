# AI Review Plugin: Two-Stage Spec & Design Review Architecture

The AI Review Plugin implements an autonomous multi-model planning and review protocol aligned with Ray Dalio's 5-Step Process and Antigravity Engineering Philosophy. It enforces a strict **Two-Stage Spec-Driven Development (SDD)** workflow to ensure architectural integrity, prevent regressions, and verify 100% bidirectional traceability before and during code implementation.

---

## Two-Stage Spec & Design Review Architecture

In complex software projects, conflating architectural design with task implementation plans causes architectural drift, unhandled edge cases, and scope creep. The Two-Stage Review Architecture decouples design from execution:

```
+-------------------------------------------------------------------------------------+
|                          SPEC-DRIVEN DEVELOPMENT WORKFLOW                           |
|                                                                                     |
|  +--------------------+        +---------------------+        +------------------+  |
|  |   BRAINSTORMING    | -----> |     SPEC-REVIEW     | -----> |  DESIGN-REVIEW   |  |
|  |  (Set Clear Goals) |        | (Validate WHAT/WHY) |        |  (Validate HOW)  |  |
|  +--------------------+        +---------------------+        +------------------+  |
|                                           |                            |            |
|                                           v                            v            |
|                                      SPEC APPROVAL               PLAN APPROVAL      |
|                                           |                            |            |
|                                           +----------------------------+            |
|                                                         |                           |
|                                                         v                           |
|                                                    SUBAGENT EXEC                    |
+-------------------------------------------------------------------------------------+
```

1. **Stage 1: Specification Tier (`spec-review`)**:
   - Focus: **WHAT & WHY**. Problem definition, domain boundaries, system topology, interfaces, failure modes, security threat models, and architectural invariants.
   - Prohibits: Granular checklists, task sequencing, file editing operations.
   - Outcome: Approved specification document stored in `docs/specs/`.
2. **Stage 2: Implementation Plan Tier (`design-review` with `SPEC_GATE`)**:
   - Focus: **HOW & SEQUENCE**. Clearly bounded operational implementation tasks formatted as checkboxes (`- [ ]`), explicit file paths, Consumes/Produces interfaces, exact test commands with expected outputs, and minimal diffs.
   - Enforces: Mandatory `SPEC_GATE` verifying bidirectional traceability between the plan and the governing specification (100% spec coverage, zero unapproved scope).

---

## Skills

### 1. `spec-review`
An on-demand skill that performs a rigorous architectural peer review on design specifications in `docs/specs/`.
- **Discovery Hierarchy**: Explicit argument `$1` -> Git modified spec (`rtk git status --porcelain docs/specs/`) -> newest file in `docs/specs/` by `mtime`.
- **Pre-flight Format Validation**: Validates title header, metadata (`Date`, `Status`, `Authors`), required sections (`Context & Motivation`, `Architecture & System Model`, `Component & Interface Contracts`, `Error Handling & Failure Modes`, `Verification & Testing`), absence of `- [ ]` checkboxes, and zero placeholders (`TODO`, `TBD`, `WIP`, ellipsis).
- **Reviewer Invocation**: Dispatches `scripts/peer_review.py --mode spec --target <SPEC_PATH> --repo .`.
- **Ray Dalio's Don't Tolerate Problems**: P0 (critical architectural flaws) and P1 (functional omissions/unhandled failure modes) block execution. P2 issues are non-blocking advisory suggestions.
- **Explicit Human Approval Gate**: Halts at `APPROVAL_GATE` per `rules/explicit-approval.md` before transitioning to implementation planning.

### 2. `design-review`
An on-demand skill that validates implementation plans and enforces bidirectional alignment with specifications.
- **`SPEC_GATE` Transition**:
  - Reads plan header for `**Spec:** <path>`.
  - Verifies the specification exists on disk.
  - Rejects with diagnostic error if spec is missing or unlinked (unless explicit `--no-spec` override is passed for bounded fixes).
- **Reviewer Invocation**: Dispatches `scripts/peer_review.py --mode design --target <plan_path> --repo . --spec <resolved_spec_path>` (or `--no-spec`).
- **Escalation Ceiling**: Enforces `attempt_counter >= 5` or `debate_counter >= 3` escalation to the human user if P0/P1 issues remain unresolved.
- **Explicit Human Approval Gate**: Halts at `APPROVAL_GATE` per `rules/explicit-approval.md` and `rules/reasoning-quality.md`. Once approved, delegates to `Antigravity /boost and invoke_subagent`.

### 3. `code-review`
The companion code review skill performs a single-pass adversarial review on code changes:
- **Two-Stage Delegation**: Flash subagent generates clean diff; Pro subagent conducts adversarial review (`attention-guard/rules/AGENTS.md`).
- **Environment Safety**: Protects temporary `GIT_INDEX_FILE` cleanup with POSIX shell trap:
  ```bash
  trap 'unset GIT_INDEX_FILE; rm -f "$GIT_INDEX_FILE"' EXIT
  ```
- **Escalation Ceiling**: Tracks attempt count and transitions to `ESCALATE` if P0/P1 blockers remain unresolved after 5 attempts.
- **Evidence Preservation**: Generates and preserves `review.md` in repository root, even when diff is empty.

---

## Modular Review Engine (`scripts/peer_review.py`)

The plugin architecture is completely modularized under `scripts/review/`:
- `review.audit`: CLI entrypoint, argument parsing, ADR context injection, and timeout management.
- `review.engines`: Multi-engine adapters (`WorkBuddyAdapter` with `deepseek-v4.1-flash` default, and `CodexAdapter`).
- `review.models`: Strict JSON schema validation, issue severity normalization (`P0`, `P1`, `P2`), and envelope formatting.
- `review.remediation`: Sanitization of prior review context to prevent instruction injection.
- `review.fsm`: State machine transitions (`AUDIT`, `REMEDIATION`, `GOVERNANCE`).
- `review.governance`: ADR indexing and requirement traceability validation.

### CLI Parameters

```bash
scripts/peer_review.py --target <path> --mode <design|code|spec> --repo <path> [--spec <path>] [--no-spec] [--engine <workbuddy|codex>] [--model <model>] [--output-file <path>]
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `--target` | String | Yes | Path to file under review (`spec.md`, `design.md`, or diff). |
| `--mode` | Enum | Yes | Review mode: `spec`, `design`, or `code`. |
| `--repo` | String | Yes | Repository root directory to mirror for context. |
| `--spec` | String | Conditional | Path to governing specification file. Required in `--mode design` unless `--no-spec` is passed. Forbidden in `--mode spec` and `--mode code`. |
| `--no-spec` | Flag | Conditional | Standalone plan review flag without governing specification. Mutually exclusive with `--spec`. Forbidden in `--mode spec` and `--mode code`. |
| `--engine` | Enum | Optional | Review engine adapter: `workbuddy` (default) or `codex`. |
| `--model` | String | Optional | Model identifier/alias (default: `deepseek-v4.1-flash` for WorkBuddy). |
| `--output-file` | String | Optional | Path to write formatted review JSON envelope atomically with `0o600` permissions. |
| `--message` | String | Optional | Follow-up message, fix summary, or technical rebuttal. |
| `--session-id` | String | Optional | Review thread session ID to resume multi-turn debate. |

### Validation Invariants & Exit Codes

- **Exit Code 0**: Review completed cleanly with zero P0/P1 issues (approved or P2 advisory only).
- **Exit Code 1**: Review completed with one or more P0 or P1 blocking issues.
- **Exit Code 2**: Fatal configuration error:
  - `--spec` and `--no-spec` passed simultaneously.
  - `--mode design` missing both `--spec` and `--no-spec`.
  - `--spec` or `--no-spec` passed with `--mode spec` or `--mode code`.
  - `--spec <path>` points to non-existent file.
  - Target or repository path does not exist.
  - Subprocess launch timeout, crash, or corrupted payload.

### Process Safety Controls

- **Graceful SIGKILL**: Verifies `process.poll() is None` before issuing `SIGKILL` after timeout grace period; never signals reaped processes.
- **PermissionError Guard**: Catches `(ProcessLookupError, PermissionError)` on all `os.killpg` calls to guard against recycled foreign PIDs.
- **Isolated Session Group**: Launches child processes with `start_new_session=True` so `os.killpg` targets an isolated session process group without leaking grandchildren.
- **Rsync Fallback**: If `rsync` is missing or fails in minimal environments, falls back gracefully to `shutil.copytree` excluding `.git`, `.gemini`, and `AGENTS.md`.

---

## Conceptual Framework: Ray Dalio's 5-Step Process

Review flows embody Ray Dalio's 5-step process for achieving operational excellence:

1. **Set Clear Goals**: Explore user intent, uncover constraints, evaluate trade-offs, and clarify requirements before drafting any plan, seamlessly integrating with Antigravity Disambiguation (/grill-me).
2. **Identify Problems (Don't Tolerate Problems)**: Surface constraints, breaking changes, and architectural risks early. Never sweep problems under the rug: P0/P1 blockers halt execution and require explicit human resolution.
3. **Diagnose Root Causes**: When a peer review rejects a plan, diagnose the fundamental root cause using attention-guard/rules/AGENTS.md (Diagnostician) rather than applying superficial fixes.
4. **Design Plans**: Formulate a comprehensive, actionable specification adhering to Antigravity Planning Mode (implementation_plan.md) (clearly bounded operational tasks, exact file paths, explicit interfaces, and concrete test commands).
5. **Push to Results (Execution)**: Enforce an explicit human approval gate per rules/explicit-approval.md and rules/reasoning-quality.md. Once approved by the user, delegate execution to Antigravity /boost and invoke_subagent with continuous verification.

---

## Installation

This plugin **must** be installed into the exact directory path `~/.gemini/config/plugins/ai-review-plugin` (or symlinked) for internal paths and skills to resolve correctly across workspaces.
