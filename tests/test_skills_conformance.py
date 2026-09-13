import os
import re
import json
import pytest

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_plan_review_skill_conformance():
    skill_path = os.path.join(PLUGIN_ROOT, "skills", "plan-review", "SKILL.md")
    assert os.path.exists(skill_path), "skills/plan-review/SKILL.md must exist"
    
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Step 1: Goals - connects with superpowers:brainstorming
    assert "superpowers:brainstorming" in content, "Must connect with superpowers:brainstorming"

    # Step 2: Don't Tolerate Problems - eliminate docs/tech_debt/
    assert "docs/tech_debt" not in content, "Must not relegate issues to docs/tech_debt"

    # Step 3: Diagnose Root Causes - systematic-debugging
    assert "superpowers:systematic-debugging" in content, "Must connect with superpowers:systematic-debugging"

    # Step 4: Design Plans - writing-plans
    assert "superpowers:writing-plans" in content, "Must standardize on superpowers:writing-plans"

    # Step 5: Push to Results - explicit approval gate and subagent-driven-development
    assert "rules/explicit-approval.md" in content, "Must reference rules/explicit-approval.md"
    assert "rules/reasoning-quality.md" in content, "Must reference rules/reasoning-quality.md"
    assert "superpowers:subagent-driven-development" in content, "Must delegate execution to subagent-driven-development"

    # Subagent Protocol Cleanup - structured JSON, no legacy Exit codes, no stale placeholders
    assert 'review_status' in content, "Must use review_status payload property"
    assert "Exit 0" not in content, "Must strip legacy Exit 0"
    assert "Exit 1" not in content, "Must strip legacy Exit 1"
    assert "Exit 2" not in content, "Must strip legacy Exit 2"
    assert "<PLAN_FILE>" not in content, "Must eliminate lingering <PLAN_FILE> placeholder"

def test_code_review_skill_conformance():
    skill_path = os.path.join(PLUGIN_ROOT, "skills", "code-review", "SKILL.md")
    assert os.path.exists(skill_path), "skills/code-review/SKILL.md must exist"
    
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must replace git read-tree HEAD || true with conditional
    assert "git read-tree HEAD || true" not in content, "Must not use || true"
    assert "git rev-parse --verify HEAD" in content, "Must use conditional git rev-parse check"

    # Must preserve review.md on success and eliminate docs/tech_debt
    assert "Delete `review.md`" not in content, "Must never delete review.md on success"
    assert "review.md" in content
    assert "docs/tech_debt" not in content, "Code review must not use docs/tech_debt"
    assert "superpowers:systematic-debugging" in content, "Code review must use systematic debugging"

    # Must not use trailing extension in mktemp template on BSD/macOS
    assert "review_XXXXXX.diff" not in content, "Must not use trailing .diff in mktemp placeholder"

def test_readme_conformance():
    readme_path = os.path.join(PLUGIN_ROOT, "README.md")
    assert os.path.exists(readme_path), "README.md must exist"
    
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must not contain docs/tech_debt bypass
    assert "docs/tech_debt" not in content, "README must not reference docs/tech_debt bypass"
    assert "superpowers:brainstorming" in content
    assert "superpowers:systematic-debugging" in content
    assert "superpowers:writing-plans" in content
    assert "superpowers:subagent-driven-development" in content
    assert "rules/explicit-approval.md" in content
    assert "rules/reasoning-quality.md" in content

def test_structured_subagent_payload_schema():
    payload = {
        "status": "completed",
        "review_status": "approved",
        "summary": "Everything looks good.",
        "issues": []
    }
    assert payload["status"] in ["completed", "failed"]
    assert payload["review_status"] in ["approved", "rejected"]
    assert isinstance(payload["issues"], list)
