---
name: tribunal
description: An on-demand skill that implements the Autonomous Multi-Model Planning Protocol.
---
# Tribunal Protocol

## Phase 1: Planning (Model A)
- Create the directory if it doesn't exist: `mkdir -p .tribunal/adr`
- Read the codebase and write the technical specification to an absolute path: `$(pwd)/.tribunal/adr/YYYYMMDD_HHMM_implementation_plan_rev<N>.md`.

## Phase 2: Peer Review Invocation (Model B)
- Run: `python3 ~/.gemini/config/plugins/ai-review-plugin/scripts/peer_review.py --mode plan --target "$(pwd)/.tribunal/adr/YYYYMMDD_HHMM_implementation_plan_rev<N>.md" --repo "$(pwd)"`
- Parse the JSON output printed to standard out. It will contain a `session_id` property.
- When `peer_review.py` outputs the JSON, save it to `.tribunal/adr/<timestamp>_review_rev<N>.json`.

## Phase 3: Consensus Evaluation & Orchestration
- **Orchestrator Paradigm**: You (the Agent) are the orchestrator. The python script is completely stateless. You must track your own attempt counter and stop at 5 attempts.
- **Analyze First**: Do not blindly accept Codex's critique. Review all P0, P1, and P2 issues critically.
- **Debate & Defend**: If an issue is out of scope, factually incorrect, or breaks the user's design, DO NOT change the plan. Instead, rerun the review using the `--message` argument to formulate a technical rebuttal and negotiate with Codex.
- **The 3-Attempt Deadlock**: If you and Codex are deadlocked (e.g., Codex refuses your rebuttal 3 times on the same P0/P1 issue), write a markdown file explaining the dispute to `.tribunal/tech_debt/<issue_name>.md`. This forces Codex to bypass it.
- **Reporting**: If you relegate a P0/P1 to technical debt, you MUST explicitly notify the User at the end of the task so they can make the final decision.
- **P2 Issues**: P2 issues are non-blocking. If you disagree with a P2, simply ignore it.
- **Exit 1 (Rejected)**: The JSON output contains P0/P1 issues. Fix the plan or formulate a rebuttal. Rerun Phase 2 adding `--session-id <SESSION_ID>` and optionally `--message`.
- **Exit 0 (Approved)**: Read the JSON for P2 advice. Proceed to execute the plan. Upon exit code 0 (Approval), generate a `consensus_summary.md` artifact summarizing the agreed-upon design/code.
- **Exit 2 (Fatal)**: Halt immediately.
