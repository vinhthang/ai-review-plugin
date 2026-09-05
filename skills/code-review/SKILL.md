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
  REVIEW_TARGET=$(mktemp "$(pwd)/.tribunal/review_XXXXXX.diff")
  if git rev-parse HEAD >/dev/null 2>&1; then git diff --cached HEAD > "$REVIEW_TARGET"; else git diff --cached 4b825dc642cb6eb9a060e54bf8d69288fbee4904 > "$REVIEW_TARGET"; fi
  if [ ! -s "$REVIEW_TARGET" ]; then
    echo "Fatal: No staged changes to review."
    rm -f "$REVIEW_TARGET"
    exit 1
  fi
  echo "REVIEW_TARGET=$REVIEW_TARGET"
  ```
- Store the printed `REVIEW_TARGET` absolute path in your agent memory for the next phases.

## Phase 2: Invocation (Model B)
- Run: `python3 ~/.gemini/config/plugins/ai-review-plugin/scripts/peer_review.py --mode code --target "<REVIEW_TARGET_FROM_PHASE_1>" --repo "$(pwd)"`
- Parse the JSON output printed to standard out. It will contain a `session_id` property.
- When `peer_review.py` outputs the JSON, save it to `docs/adr/<timestamp>_review_rev<N>.json`.

## Phase 3: Consensus & Orchestration
- **Orchestrator Paradigm**: You (the Agent) are the orchestrator. The python script is completely stateless. You must track your own attempt counter and stop at 5 attempts.
- **Analyze First**: Do not blindly accept Codex's critique. Review all P0, P1, and P2 issues critically.
- **Debate & Defend**: If an issue is out of scope, factually incorrect, or breaks the user's design, DO NOT change the code. Instead, rerun the review using the `--message` argument to formulate a technical rebuttal and negotiate with Codex.
- **The 3-Attempt Deadlock**: If you and Codex are deadlocked (e.g., Codex refuses your rebuttal 3 times on the same P0/P1 issue), write a markdown file explaining the dispute to `docs/tech_debt/<issue_name>.md`. This forces Codex to bypass it.
- **Reporting**: If you create a technical debt file in `docs/tech_debt/` to bypass a P0/P1 issue, you MUST STOP execution and request explicit User approval before proceeding. Do not automatically proceed to implementation.
- **P2 Issues**: P2 issues are non-blocking. If you disagree with a P2, simply ignore it.
- **Exit 1**: Fix code or formulate a rebuttal, STAGE the fixes with `git add <files>` (if any), REGENERATE the diff to the SAME `<REVIEW_TARGET_FROM_PHASE_1>`, retry passing `--session-id <SESSION_ID>` and optionally `--message`.
- **Exit 0**: Proceed. Upon exit code 0 (Approval), delete `<REVIEW_TARGET_FROM_PHASE_1>` (unless retention is requested) and generate a `consensus_summary.md` artifact summarizing the agreed-upon design/code.
- **Exit 2**: Halt. Delete `<REVIEW_TARGET_FROM_PHASE_1>` before halting.
