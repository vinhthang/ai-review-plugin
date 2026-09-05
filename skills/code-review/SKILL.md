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
- Run: `python ~/.gemini/config/plugins/ai-review-plugin/scripts/peer_review.py --mode code --target "$DIFF_PATH" --repo $(pwd) [--debug]`
- Capture `<WORK_DIR>` from stdout.
## Phase 3: Consensus
- **Exit 1**: Fix code, REGENERATE the diff to the SAME `"$DIFF_PATH"`, retry passing `--work-dir`.
- **Exit 0**: Proceed.
- **Exit 2**: Halt.
