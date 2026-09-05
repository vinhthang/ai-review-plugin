import re

with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'r') as f:
    content = f.read()

# Fix the duplicate mermaid diagram
content = re.sub(r'```mermaid\nstateDiagram-v2\n    \[\*\] --> INIT\n    INIT --> PREPARE\n    PREPARE --> ABORT : Preparation Failure\n    PREPARE --> REVIEW : attempt_counter == 0\n    PREPARE --> SELF_REVIEW : attempt_counter > 0\n    SELF_REVIEW --> REVIEW : Fix is adequate\n    SELF_REVIEW --> FIX : Fix is flawed\n    REVIEW --> EVALUATE\n    \.\.\.\n```\n\n', '', content)

# Fix PREPARE State Transition Updates
prepare_updates = """**2b. PREPARE State Transition Updates**
Update the transition logic in `PREPARE` to route based on the attempt counter:
```markdown
**Transitions:**
- On failure (e.g. empty diff, command failure) -> Transition to `ABORT`
- On success and `attempt_counter == 0` -> Transition to `REVIEW`
- On success and `attempt_counter > 0` -> Transition to `SELF_REVIEW`
```"""
content = re.sub(r'\*\*2b\. PREPARE State Transition Updates\*\*.*?```', prepare_updates, content, flags=re.DOTALL)

# Add missing ``` at the end of SELF_REVIEW State
content = re.sub(r'-> Transition to `ESCALATE` \(or `ABORT` if appropriate\)\n\n\n## Verification', '-> Transition to `ESCALATE` (For code-review) or `ABORT` (For tribunal)\n```\n\n## Verification', content)


with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'w') as f:
    f.write(content)
