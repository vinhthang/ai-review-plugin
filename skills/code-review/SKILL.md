---
name: code-review
description: An on-demand skill that performs a one-shot peer review on code changes and outputs findings to review.md.
---
# Code Review

This skill performs a single-pass adversarial code review by spawning a `pro` (Opus) subagent. It does NOT negotiate or retry — it produces a `review.md` file with P0/P1/P2 findings for the agent to reconcile.

## Steps

### 1. Generate Diff
- Identify the explicit list of files you modified or created for this task.
- Generate a comprehensive diff using a temporary index to preserve the user's working state:
  ```bash
  mkdir -p .code-review
  REVIEW_TARGET=$(mktemp "$(pwd)/.code-review/review_XXXXXX")
  export GIT_INDEX_FILE=$(mktemp -u)
  if git rev-parse --verify HEAD >/dev/null 2>&1; then git read-tree HEAD; fi
  git add <FILES>
  if git rev-parse --verify HEAD >/dev/null 2>&1; then git diff --cached HEAD > "$REVIEW_TARGET"; else git diff --cached 4b825dc642cb6eb9a060e54bf8d69288fbee4904 > "$REVIEW_TARGET"; fi
  if ! test -s "$REVIEW_TARGET"; then rm -f "$REVIEW_TARGET" "$GIT_INDEX_FILE"; echo "No changes to review."; exit 0; fi
  rm "$GIT_INDEX_FILE"
  unset GIT_INDEX_FILE
  ```

### 2. Submit for Review
- Use `invoke_subagent` with `Model: pro` to spawn a Peer Reviewer subagent.
- Pass the diff content along with the `implementation_plan.md` (if it exists) for context.
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

### 3. Save Results
- Write the reviewer's findings to `review.md` in the project root directory.
- Format with sections: Executive Summary, P0 Issues (Critical), P1 Issues (Blocking), P2 Issues (Advisory).
- Delete the temporary `<REVIEW_TARGET>` diff file.
- Use `manage_subagents` to kill the Peer Reviewer subagent.

### 4. Evaluate Results
- **Preserve Verification Evidence**: Never delete `review.md`. It serves as the authoritative verification artifact proving the code was scrutinized.
- If P0/P1 issues were found (`review_status == "rejected"`):
  - Retain `review.md` in the project root.
  - Do NOT tolerate problems or sweep them under the rug. P0/P1 blockers must be diagnosed and fixed before completion.
  - Reconcile findings against `implementation_plan.md` using `superpowers:systematic-debugging` to identify root causes prior to making any code corrections.
  - After diagnosing root causes and implementing fixes, re-run this code review protocol to verify all P0/P1 blockers are resolved and `review_status == "approved"`.
- If no P0/P1 issues were found (`review_status == "approved"`):
  - Retain `review.md` in the project root as verification evidence.
  - The Primary Agent compiles the final Architecture Decision Record to `docs/adr/YYYYMMDD_HHMM_<description>.md` referencing `implementation_plan.md`, `review.md`, and the verified code changes.
