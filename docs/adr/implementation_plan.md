# Tribunal Debug Mode & Concurrency Architecture Plan

## Goal
Add an optional "Debug Mode" and guarantee concurrency safety for the Tribunal protocol. Codex reviews have revealed that relying on the agent to manage the state machine across multiple isolated `run_command` shell sessions is intrinsically unsafe (shell variables die, traps execute early, and concurrent runs clash). We will centralize the state machine into a bulletproof Bash script.

## Proposed Changes

### [NEW] [scripts/tribunal.sh](file:///Users/thanghoang/github/ai-review-plugin/scripts/tribunal.sh)
Create a monolithic, checked-in helper script that owns the entire lifecycle, ensuring one process owns `$WORK_DIR`, traps, retries, and variables.
- **Arguments**: `--debug` (optional flag to retain artifacts), `--plan <path>` (the draft plan written by Model A).
- **Initialization**:
  - `WORK_DIR=$(mktemp -d -t tribunal_run_XXXXXX)`
  - Validate `$WORK_DIR` starts with the system temp directory before allowing any `rm -rf`.
  - Set a single shell `trap` to securely `rm -rf "$WORK_DIR"` on `EXIT`, unless `--debug` is passed.
- **Lifecycle (Inside the script)**:
  - Copy the agent's draft plan to `$WORK_DIR/plan.md`.
  - Loop up to 5 times:
    - Run `codex exec` pointing exactly to `$WORK_DIR/plan.md` (via `--file "$WORK_DIR/plan.md"` or prompt attachment).
    - Capture `CODEX_EXIT=$?`.
    - If `--debug`, archive `$WORK_DIR` artifacts into `$WORK_DIR/attempt_$Attempt`.
    - If `approved == true`, output the final consensus and exit `0`.
    - If `approved == false`, output the blocking issues to stdout, clean up transient `review.json` from `$WORK_DIR` (but keep the blocking issues in memory to print), and exit `1` to let Model A rewrite the plan.

### [MODIFY] [SKILL.md](file:///Users/thanghoang/github/ai-review-plugin/skills/tribunal/SKILL.md)
Refactor the agent instructions to delegate the state machine to the new script:
- **Phase 1**: Write the technical specification to a temporary file (e.g., `scratch/plan_draft.md`).
- **Phase 2**: Run `./scripts/tribunal.sh [--debug] --plan scratch/plan_draft.md`.
  - If the script exits `0`, read the final plan and execute it.
  - If the script exits `1`, read the blocking issues printed to stdout, update `scratch/plan_draft.md`, and repeat Phase 2.

### [MODIFY] [README.md](file:///Users/thanghoang/github/ai-review-plugin/README.md)
- Document the new `scripts/tribunal.sh` architecture.
- Document that concurrent runs are safely isolated in `mktemp` directories, and final execution operates directly from the agent's isolated draft plan without clashing in the repo root.
- Document the debug mode flag `--debug`.
