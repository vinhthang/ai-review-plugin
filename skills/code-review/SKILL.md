---
name: code-review
description: An on-demand skill that performs a one-shot peer review on code changes and outputs findings to review.md.
---
# Code Review

This skill performs a single-pass adversarial code review using an explicit two-stage delegation workflow to comply with Attention Guard rules. The Primary Agent delegates terminal execution to subagents according to the Model Selection Framework. It does NOT negotiate or retry — it produces a `review.md` file with P0/P1/P2 findings for the agent to reconcile.

## Steps

### Stage 1: Generate Diff (Flash Subagent)
- The Primary Agent MUST NOT execute terminal commands directly in Phase 1 per `attention-guard/rules/AGENTS.md`.
- Set a liveness timer via `schedule` with `TimerCondition: any` (e.g., `DurationSeconds=300`) per `attention-guard/rules/AGENTS.md` before spawning the subagent.
- Use `invoke_subagent` with `Model: flash` to spawn a diff generation subagent.
- Provide the subagent with the explicit list of files modified or created for this task.
- The `flash` subagent runs the diff script using `rtk git` command prefixing per `rules/rtk.md` and a temporary index to preserve the user's working state, with a POSIX signal trap to ensure `GIT_INDEX_FILE` environment variable cleanup (ISSUE-R2-01):
  ```bash
  mkdir -p .code-review
  REVIEW_TARGET=$(mktemp "$PWD/.code-review/review_XXXXXX")
  export GIT_INDEX_FILE=$(mktemp -u)
  trap 'unset GIT_INDEX_FILE; rm -f "$GIT_INDEX_FILE"' EXIT
  if rtk git rev-parse --verify HEAD >/dev/null 2>&1; then rtk git read-tree HEAD; fi
  rtk git add <FILES>
  if rtk git rev-parse --verify HEAD >/dev/null 2>&1; then rtk git diff --cached HEAD > "$REVIEW_TARGET"; else rtk git diff --cached 4b825dc642cb6eb9a060e54bf8d69288fbee4904 > "$REVIEW_TARGET"; fi
  if ! test -s "$REVIEW_TARGET"; then
    rm -f "$REVIEW_TARGET"
    cat << 'EOF' > review.md
  # Code Review: Clean
  **Status**: Approved (No changes to review)
  No modified files or differences detected against target.
  EOF
    echo "No changes to review."
    exit 0
  fi
  rm -f "$GIT_INDEX_FILE"
  unset GIT_INDEX_FILE
  ```
- The `flash` subagent returns the `$REVIEW_TARGET` path via `send_message` with a strict JSON payload:
  ```json
  {
    "status": "completed",
    "summary": "Diff generated successfully",
    "review_target": "/absolute/path/to/.code-review/review_XXXXXX"
  }
  ```
- **Empty Diff Handling (ISSUE-R3-03)**: If no changes were detected, the subagent writes `review.md` documenting clean verification evidence and returns `{"status": "completed", "summary": "No changes to review", "review_target": null}`. `review.md` is preserved in the project root as mandatory verification evidence, and review terminates early.
- The Primary Agent uses `manage_subagents` to terminate the diff generation subagent.

### Stage 2: Adversarial Peer Review (Pro Subagent)
- Set a liveness timer via `schedule` with `TimerCondition: any` (e.g., `DurationSeconds=300`) per `attention-guard/rules/AGENTS.md`.
- Use `invoke_subagent` with `Model: pro` to spawn a Peer Reviewer subagent to conduct the adversarial review on that diff.
- Execute adversarial review via peer review CLI:
  `rtk python3 scripts/peer_review.py --mode code --repo . --output-file review.json`
- Pass the diff content from `$REVIEW_TARGET` along with the `implementation_plan.md` (if it exists) for context.
- Instruct the reviewer to apply the `superpowers` rule and output findings as a structured JSON payload:
  ```json
  {
    "status": "completed",
    "review_status": "approved|rejected",
    "summary": "Executive summary of the code review",
    "issues": [
      {
        "severity": "P0|P1|P2",
        "description": "Clear explanation of the defect and location"
      }
    ]
  }
  ```

### Stage 3: Save Results
- Write the reviewer's findings to `review.md` in the project root directory.
- Format with sections: Executive Summary, P0 Issues (Critical), P1 Issues (Blocking), P2 Issues (Advisory).
- Delete the temporary `$REVIEW_TARGET` diff file.
- Use `manage_subagents` to kill the Peer Reviewer subagent.

### Stage 4: Evaluate Results
- **Preserve Verification Evidence (ISSUE-R3-03)**: Never delete `review.md`. It serves as the authoritative verification artifact proving the code was scrutinized. Even on clean diffs or zero-defect passes, `review.md` must be retained in the project root.
- **Attempt Tracking & Escalation Ceiling (ISSUE-R3-02)**: Maintain an attempt counter (`attempt_counter`). If P0/P1 blockers remain unresolved after 5 attempts (`attempt_counter >= 5`), stop autonomous looping and transition to `ESCALATE` (present the unresolved blockers, trade-offs, and root cause findings to the human user).
- If P0/P1 issues were found (`review_status == "rejected"` with blocking defects):
  - Retain `review.md` in the project root.
  - Do NOT tolerate problems or sweep them under the rug. P0/P1 blockers must be diagnosed and fixed before completion.
  - Reconcile findings against `implementation_plan.md` using `superpowers:systematic-debugging` to identify root causes prior to making any code corrections.
  - After diagnosing root causes and implementing fixes, increment `attempt_counter`. If `attempt_counter >= 5`, transition to `ESCALATE`. Otherwise, re-run this code review protocol to verify all P0/P1 blockers are resolved and `review_status == "approved"`.
- If no P0/P1 issues were found (`review_status == "approved"` or P2 advisory issues only):
  - Treat P2 advisory issues as non-blocking suggestions.
  - Retain `review.md` in the project root as verification evidence.
  - The Primary Agent compiles the final Architecture Decision Record to `docs/adr/YYYYMMDD_HHMM_<description>.md` referencing `implementation_plan.md`, `review.md`, and the verified code changes.
