---
name: tribunal
description: An on-demand skill that implements the Autonomous Multi-Model Planning Protocol.
---
# Tribunal Protocol

## Phase 1: Planning (Model A)
- Create the directory if it doesn't exist: `mkdir -p .tribunal/adr`
- Read the codebase and write the technical specification to an absolute path: `$(pwd)/.tribunal/adr/YYYYMMDD_HHMM_implementation_plan_rev<N>.md`.

## Phase 2: Peer Review Invocation (Model B)
- Run: `python3 ~/.gemini/config/plugins/ai-review-plugin/scripts/peer_review.py --mode plan --target "$(pwd)/.tribunal/adr/YYYYMMDD_HHMM_implementation_plan_rev<N>.md" --repo "$(pwd)" --debug`
- Parse the JSON output printed to standard out. It will contain a `session_id` property.

## Phase 3: Consensus Evaluation & Orchestration
- **Orchestrator Paradigm**: You (the Agent) are the orchestrator. The python script is completely stateless. You must track your own attempt counter and stop at 5 attempts.
- **Exit 1 (Rejected)**: The JSON output contains P0/P1 issues. Update the plan. Rerun Phase 2 adding `--session-id <SESSION_ID>`. You may pass `--message` to debate.
- **Exit 0 (Approved)**: Read the JSON for P2 advice. Proceed to execute the plan.
- **Exit 2 (Fatal)**: Halt immediately.
