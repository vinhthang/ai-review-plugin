import re

with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'r') as f:
    content = f.read()

# Add INIT state update for counter
init_update = """**2. INIT State Updates**
Update the `INIT` state to initialize `self_review_counter` to 0. Reset it to 0 inside `EVALUATE` if the outcome is to fix (so each new Codex loop gets 3 self-review attempts).

**2b. PREPARE State Transition Updates**"""
content = re.sub(r'\*\*2\. PREPARE State Transition Updates\*\*', init_update, content)

# Fix transitions in SELF_REVIEW
self_review_transitions = """**Transitions:**
- If the fix is adequate -> Transition to `REVIEW` (to submit to Codex)
- If the fix is flawed or incomplete and `self_review_counter < 3` -> Transition to `FIX` (to modify again)
- If the fix is flawed or incomplete and `self_review_counter >= 3` -> Transition to `ESCALATE` (For code-review) or `ABORT` (For tribunal)"""

content = re.sub(r'\*\*Transitions:\*\*.*?```', self_review_transitions + '\n```', content, flags=re.DOTALL)

with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'w') as f:
    f.write(content)
