import re

with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'r') as f:
    content = f.read()

# I will rewrite the whole file to make it perfect
new_content = """# Implementation Plan: Adding Self-Review State to SKILL.md

We are optimizing the State Machine architecture in `skills/code-review/SKILL.md` and `skills/tribunal/SKILL.md` to reduce unnecessary Codex API calls. We will introduce a `SELF_REVIEW` state that acts as a pre-flight check before retries.

## Proposed Changes

### [MODIFY] skills/code-review/SKILL.md & skills/tribunal/SKILL.md
We will update the Mermaid diagrams and State definitions in both files.

**1. Mermaid Diagram Updates**
Add `SELF_REVIEW` to the diagram:
```mermaid
stateDiagram-v2
    [*] --> INIT
    INIT --> PREPARE
    PREPARE --> ABORT : Preparation Failure
    PREPARE --> REVIEW : attempt_counter == 0
    PREPARE --> SELF_REVIEW : attempt_counter > 0
    SELF_REVIEW --> REVIEW : Fix is adequate
    SELF_REVIEW --> FIX : Fix is flawed (self_review_counter < 3)
    SELF_REVIEW --> ESCALATE : Fix is flawed (self_review_counter >= 3)
    REVIEW --> EVALUATE
    ...
```

**2. INIT State Updates**
Update the `INIT` state to initialize `self_review_counter` to 0. Reset it to 0 inside `EVALUATE` if the outcome is to fix (so each new Codex loop gets 3 self-review attempts).

**2b. PREPARE State Transition Updates**
Update the transition logic in `PREPARE` to route based on the attempt counter:
```markdown
**Transitions:**
- On failure (e.g. empty diff, command failure) -> Transition to `ABORT`
- On success and `attempt_counter == 0` -> Transition to `REVIEW`
- On success and `attempt_counter > 0` -> Transition to `SELF_REVIEW`
```

**3. New SELF_REVIEW State**
Insert the new state before `REVIEW`:
```markdown
### State: SELF_REVIEW
**Action:**
- You are acting as a Pre-Reviewer.
- For `code-review`: Read the contents of the `<REVIEW_TARGET>` file. Evaluate if the code modifications solve the issues without regressions.
- For `tribunal`: Read the contents of the `<PLAN_FILE>` file. Evaluate if the plan revisions address prior findings without regressions.
- Compare the changes against the P0/P1 issues that Codex raised in the previous iteration.
- Increment the `self_review_counter`.

**Transitions:**
- If the fix is adequate -> Transition to `REVIEW` (to submit to Codex)
- If the fix is flawed or incomplete and `self_review_counter < 3` -> Transition to `FIX` (to modify again)
- If the fix is flawed or incomplete and `self_review_counter >= 3` -> Transition to `ESCALATE`
```

## Verification
We will verify this implementation plan by running it through the `tribunal` peer review protocol (Model B) before modifying the codebase.
We will add explicit post-change checks for both state machines:
- initial review bypasses SELF_REVIEW
- a rejected-and-fixed attempt enters SELF_REVIEW
- adequate fixes reach REVIEW
- flawed fixes return to FIX
- debates resume REVIEW directly
- the new loop guard terminates if self_review_counter >= 3
"""

with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'w') as f:
    f.write(new_content)
