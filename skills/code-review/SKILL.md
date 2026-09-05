---
name: code-review
description: An on-demand skill that performs a rigorous multi-model peer review on code changes.
---
# Code Review Protocol

## Phase 1: Preparation (Model A)
- Stage your changes using `git add <files>`.
- Generate a comprehensive diff saving to a unique absolute path:
  ```bash
  mkdir -p .tribunal
  DIFF_PATH=$(mktemp .tribunal/code_review_XXXXXX.diff)
  if git rev-parse HEAD >/dev/null 2>&1; then git diff --cached HEAD > "$DIFF_PATH"; else git diff --cached 4b825dc642cb6eb9a060e54bf8d69288fbee4904 > "$DIFF_PATH"; fi
  ```

## Phase 2: Invocation (Model B)
- Run: `python3 ~/.gemini/config/plugins/ai-review-plugin/scripts/peer_review.py --mode code --target "$DIFF_PATH" --repo "$(pwd)"`
- Parse the JSON output printed to standard out. It will contain a `session_id` property.
- When `peer_review.py` outputs the JSON, save it to `.tribunal/adr/<timestamp>_review_rev<N>.json`.

## Phase 3: Consensus & Orchestration
- **Orchestrator Paradigm**: You (the Agent) are the orchestrator. The python script is completely stateless. You must track your own attempt counter and stop at 5 attempts.
- **Exit 1**: Fix code, STAGE the fixes with `git add <files>`, REGENERATE the diff to the SAME `"$DIFF_PATH"`, retry passing `--session-id <SESSION_ID>`.
- **Exit 0**: Proceed. Upon exit code 0 (Approval), generate a `consensus_summary.md` artifact summarizing the agreed-upon design/code.
- **Exit 2**: Halt.
