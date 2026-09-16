import os
import re
import json
import ast
import pytest

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_spec_review_skill_conformance():
    skill_path = os.path.join(PLUGIN_ROOT, "skills", "spec-review", "SKILL.md")
    assert os.path.exists(skill_path), "skills/spec-review/SKILL.md must exist"

    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Frontmatter
    assert "name: spec-review" in content, "Must have name: spec-review in frontmatter"
    assert "docs/superpowers/specs/" in content, "Description/content must target specs directory"

    # Ray Dalio 5-Step mappings & Superpowers connections
    assert "superpowers:brainstorming" in content, "Must connect with superpowers:brainstorming"
    assert "docs/tech_debt" not in content, "Must not relegate issues to docs/tech_debt"
    assert "superpowers:systematic-debugging" in content, "Must connect with superpowers:systematic-debugging"
    assert "superpowers:writing-plans" in content, "Must connect with superpowers:writing-plans"
    assert "rules/explicit-approval.md" in content, "Must reference rules/explicit-approval.md"
    assert "attention-guard/rules/AGENTS.md" in content, "Must cite attention-guard/rules/AGENTS.md"
    assert "rules/agent-delegation.md" not in content, "Must not cite outdated rules/agent-delegation.md"

    # Numbered Mermaid diagram transitions
    assert "Audit --> Governance : 1. Clean" in content
    assert "Audit --> Remediation : 2. Defects Found" in content
    assert "Remediation --> Audit : 3. Re-Audit Loop" in content
    assert "Remediation --> Governance : 4. Escalated" in content
    assert "Governance --> Done : 5. Approved" in content

    # P2-Only Guard
    assert "P2-Only Guard" in content, "Must include P2-Only Guard"

    # Clean subagent protocols - no legacy Exit codes, proper payload schema
    assert "review_status" in content, "Must use review_status payload property"
    assert "Exit 0" not in content, "Must strip legacy Exit 0"
    assert "Exit 1" not in content, "Must strip legacy Exit 1"
    assert "Exit 2" not in content, "Must strip legacy Exit 2"

    # Review command
    assert "--mode spec" in content, "Must use --mode spec in reviewer dispatch"
    assert "--output-file review.json" in content, "Must document --output-file review.json"
    assert "scripts/peer_review.py" in content, "Must invoke scripts/peer_review.py"

def test_design_review_skill_conformance():
    skill_path = os.path.join(PLUGIN_ROOT, "skills", "design-review", "SKILL.md")
    assert os.path.exists(skill_path), "skills/design-review/SKILL.md must exist"
    
    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Frontmatter
    assert "name: design-review" in content

    # Ray Dalio 5-Step mappings & Superpowers connections
    assert "superpowers:brainstorming" in content, "Must connect with superpowers:brainstorming"
    assert "docs/tech_debt" not in content, "Must not relegate issues to docs/tech_debt"
    assert "superpowers:systematic-debugging" in content, "Must connect with superpowers:systematic-debugging"
    assert "superpowers:writing-plans" in content, "Must standardize on superpowers:writing-plans"
    assert "rules/explicit-approval.md" in content, "Must reference rules/explicit-approval.md"
    assert "rules/reasoning-quality.md" in content, "Must reference rules/reasoning-quality.md"
    assert "superpowers:subagent-driven-development" in content, "Must delegate execution to subagent-driven-development"
    assert "attention-guard/rules/AGENTS.md" in content, "Must cite attention-guard/rules/AGENTS.md"
    assert "rules/agent-delegation.md" not in content, "Must not cite outdated rules/agent-delegation.md"

    # Numbered Mermaid diagram transitions
    assert "Audit --> Governance : 1. Clean" in content
    assert "Audit --> Remediation : 2. Defects Found" in content
    assert "Remediation --> Audit : 3. Re-Audit Loop" in content
    assert "Remediation --> Governance : 4. Escalated" in content
    assert "Governance --> Done : 5. Approved" in content

    # Subagent Protocol Cleanup - structured JSON, no legacy Exit codes, no stale placeholders
    assert 'review_status' in content, "Must use review_status payload property"
    assert "Exit 0" not in content, "Must strip legacy Exit 0"
    assert "Exit 1" not in content, "Must strip legacy Exit 1"
    assert "Exit 2" not in content, "Must strip legacy Exit 2"
    assert "<PLAN_FILE>" not in content, "Must eliminate lingering <PLAN_FILE> placeholder"

    # Design-review hardening: P2-only rejection guard
    assert "P2-Only Guard" in content

    # Review command and output persistence
    assert "--output-file review.json" in content, "Must document --output-file review.json"
    assert "scripts/peer_review.py" in content, "Must invoke scripts/peer_review.py"
    assert "--no-spec" in content, "Must support --no-spec flag for standalone plans"

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
    assert '$(pwd)' not in content, "code-review skill must avoid $(pwd) command substitution"
    assert 'REVIEW_TARGET=$(mktemp "$PWD/.code-review/review_XXXXXX")' in content, "code-review skill must use $PWD for absolute path"

    # Two-stage delegation workflow to prevent Attention Guard deadlock
    assert "--output-file review.json" in content, "Must document --output-file review.json"
    assert "scripts/peer_review.py" in content, "Must invoke scripts/peer_review.py"
    assert "Stage 1: Generate Diff" in content, "Must define Stage 1 diff generation"
    assert "Stage 2: Adversarial Peer Review" in content, "Must define Stage 2 adversarial review"
    assert "Model: flash" in content, "Stage 1 must use flash subagent"
    assert "Model: pro" in content, "Stage 2 must use pro subagent"
    assert "$REVIEW_TARGET" in content, "Must reference $REVIEW_TARGET path"

    # rtk git prefixing
    assert "rtk git rev-parse --verify HEAD" in content, "Must prefix git with rtk"
    assert "rtk git read-tree HEAD" in content, "Must prefix git with rtk"
    assert "rtk git add <FILES>" in content, "Must prefix git with rtk"
    assert "rtk git diff --cached" in content, "Must prefix git with rtk"

    # schedule liveness tracking per AGENTS.md
    assert "TimerCondition: any" in content, "Must use schedule with TimerCondition: any"
    assert "attention-guard/rules/AGENTS.md" in content, "Must cite attention-guard/rules/AGENTS.md"

    # Stage structure and subagent lifecycle management
    assert "Stage 3: Save Results" in content, "Must define Stage 3 Save Results"
    assert "Stage 4: Evaluate Results" in content, "Must define Stage 4 Evaluate Results"
    assert "manage_subagents" in content, "Must manage subagent lifecycle"

    # R4 / ISSUE-R2-01: Signal trap for GIT_INDEX_FILE
    assert "trap 'unset GIT_INDEX_FILE" in content, "Must protect GIT_INDEX_FILE cleanup with shell trap"

    # R4 / ISSUE-R3-02: Attempt ceiling and ESCALATE transition
    assert "attempt_counter >= 5" in content or "attempt_counter" in content
    assert "ESCALATE" in content, "Must define ESCALATE transition for code review blockers"

    # R4 / ISSUE-R3-03: Preservation of review.md even on empty diff
    assert "review.md" in content
    assert "No changes to review" in content

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

def test_peer_review_conformance():
    script_path = os.path.join(PLUGIN_ROOT, "scripts", "peer_review.py")
    assert os.path.exists(script_path), "scripts/peer_review.py must exist"
    
    with open(script_path, "r", encoding="utf-8") as f:
        source = f.read()

    # Rule: no-error-suppression
    assert "except BaseException: pass" not in source, "Must not swallow BaseException with pass"
    assert "except Exception: pass" not in source, "Must not swallow Exception with pass"
    assert "json.JSONDecodeError" in source, "Must explicitly catch json.JSONDecodeError"
    assert "sys.stderr" in source, "Must log errors to sys.stderr"

    # Check AST to ensure NO pass statements exist in any except handler per rules/no-error-suppression.md
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            for stmt in node.body:
                if isinstance(stmt, ast.Pass):
                    handler_name = ast.unparse(node.type) if node.type else "bare except"
                    pytest.fail(f"Pass statement in except block for '{handler_name}' is forbidden per rules/no-error-suppression.md")

    # Check that every open() call in peer_review.py specifies encoding="utf-8"
    open_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"
    ]
    assert len(open_calls) > 0, "Must have open() calls"
    for call in open_calls:
        encoding_kw = next((kw for kw in call.keywords if kw.arg == "encoding"), None)
        assert encoding_kw is not None, "Every open() call must specify encoding"
        assert isinstance(encoding_kw.value, ast.Constant) and encoding_kw.value.value == "utf-8", "encoding must be 'utf-8'"

def test_obsolete_files_cleaned():
    tech_debt_dir = os.path.join(PLUGIN_ROOT, "docs", "tech_debt")
    adr_plan = os.path.join(PLUGIN_ROOT, "docs", "adr", "implementation_plan.md")
    assert not os.path.exists(tech_debt_dir), "docs/tech_debt/ directory must be deleted"
    assert not os.path.exists(adr_plan), "docs/adr/implementation_plan.md must be deleted"


def test_skills_recursive_discovery_conformance():
    spec_skill = os.path.join("skills", "spec-review", "SKILL.md")
    design_skill = os.path.join("skills", "design-review", "SKILL.md")
    with open(spec_skill, "r") as f:
        s_text = f.read()
    with open(design_skill, "r") as f:
        d_text = f.read()
    assert "**" in s_text, "spec-review must declare recursive discovery pattern"
    assert "**" in d_text, "design-review must declare recursive discovery pattern"


def test_modular_review_architecture_conformance():
    spec_skill = os.path.join("skills", "spec-review", "SKILL.md")
    design_skill = os.path.join("skills", "design-review", "SKILL.md")
    index_file = os.path.join("docs", "superpowers", "specs", "INDEX.md")

    with open(spec_skill, "r", encoding="utf-8") as f:
        s_text = f.read()
    with open(design_skill, "r", encoding="utf-8") as f:
        d_text = f.read()
    with open(index_file, "r", encoding="utf-8") as f:
        idx_text = f.read()

    # 1. Assert semantic stage declarations (Audit, Remediation, Governance)
    for stage in ("### Audit", "### Remediation", "### Governance"):
        assert stage in s_text, f"spec-review missing {stage}"
        assert stage in d_text, f"design-review missing {stage}"

    # 2. Assert numbered state transitions in diagrams
    for transition in ("1. Clean", "2. Defects Found", "3. Re-Audit Loop", "4. Escalated"):
        assert transition in s_text, f"spec-review missing numbered transition {transition}"
        assert transition in d_text, f"design-review missing numbered transition {transition}"

    # 3. Assert absence of obsolete monolithic states
    for obsolete in ("SELF_REVIEW", "attempt_counter >= 5", "debate_counter"):
        assert obsolete not in s_text, f"spec-review still contains obsolete pattern {obsolete}"
        assert obsolete not in d_text, f"design-review still contains obsolete pattern {obsolete}"

    # 4. Assert INDEX.md registers the modular flows feature
    assert "2026-09-16-modular-review-flows" in idx_text
    assert "REQ-021" in idx_text
