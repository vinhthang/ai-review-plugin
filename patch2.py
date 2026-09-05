import re

with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'r') as f:
    content = f.read()

# Fix the duplicate markdown block caused by the previous regex replacement
content = re.sub(r'```markdown\n### State: SELF_REVIEW\n\*\*Action:\*\*\n- You are acting as a Pre-Reviewer\.\n- Read the contents of the `<REVIEW_TARGET>` file\.\n- Compare the changes against the P0/P1 issues that Codex raised in the previous iteration\.\n- Critically evaluate if your code modifications actually solve the issues without introducing new regressions\.\n\n\*\*Transitions:\*\*\n- If the fix is adequate -> Transition to `REVIEW` \(to submit to Codex\)\n- If the fix is flawed or incomplete -> Transition to `FIX` \(to modify the codebase again\)\n```', '', content)

# Clean up Mermaid Diagram Updates to include ESCALATE transition
mermaid_update = """**1. Mermaid Diagram Updates**
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
```"""
content = re.sub(r'\*\*1\. Mermaid Diagram Updates\*\*.*?```', mermaid_update, content, flags=re.DOTALL)


with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'w') as f:
    f.write(content)
