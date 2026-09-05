---
name: tribunal
description: An on-demand skill that implements the Autonomous Multi-Model Planning Protocol.
---
# Tribunal Protocol
## Phase 1: Planning (Model A)
- Read the codebase and write the technical specification to an absolute path: `$(pwd)/.tribunal/adr/YYYYMMDD_HHMM_implementation_plan_rev<N>.md`.
## Phase 2: Peer Review Invocation (Model B)
- Run: `python ~/.gemini/config/plugins/ai-review-plugin/scripts/peer_review.py --mode plan --target $(pwd)/.tribunal/adr/YYYYMMDD_HHMM_implementation_plan_rev<N>.md --repo $(pwd) --debug`
- Capture the `<WORK_DIR>` printed on the first line of stdout.
## Phase 3: Consensus Evaluation
- **Post-Review Artifacts**: After the review completes (whether approved or rejected), copy the `review.json` from `<WORK_DIR>/review.json` into the ADR folder next to the plan: `$(pwd)/.tribunal/adr/YYYYMMDD_HHMM_review_rev<N>.json`.
- **Exit 1 (Rejected)**: Read stderr issues. Update the plan. Rerun Phase 2 adding `--work-dir <WORK_DIR>`. You may pass `--message` to debate.
- **Exit 0 (Approved)**: Read stdout for P2 advice. Proceed to execute the plan.
- **Exit 2 (Fatal)**: Halt immediately.
