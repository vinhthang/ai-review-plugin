import re

with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'r') as f:
    content = f.read()

new_self_review = """**3. New SELF_REVIEW State**
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
- If the fix is flawed or incomplete and `self_review_counter >= 3` -> Transition to `ESCALATE` (or `ABORT` if appropriate)
```"""

content = re.sub(r'\*\*3\. New SELF_REVIEW State\*\*.*?```', new_self_review, content, flags=re.DOTALL)

verification_text = """## Verification
We will verify this implementation plan by running it through the `tribunal` peer review protocol (Model B) before modifying the codebase.
We will add explicit post-change checks for both state machines:
- initial review bypasses SELF_REVIEW
- a rejected-and-fixed attempt enters SELF_REVIEW
- adequate fixes reach REVIEW
- flawed fixes return to FIX
- debates resume REVIEW directly
- the new loop guard terminates if self_review_counter >= 3"""

content = re.sub(r'## Verification.*', verification_text, content, flags=re.DOTALL)


with open('/Users/thanghoang/.gemini/antigravity/brain/852848c7-0349-408e-a569-6987f5e8a216/implementation_plan.md', 'w') as f:
    f.write(content)
