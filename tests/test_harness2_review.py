#!/usr/bin/env python3
"""
Unit and integration tests for Harness² Review improvements:
- REQ-045: Sandbox Verdict Anti-Leak & Tripwire in scripts/review/audit.py
- REQ-046: Orthogonal INV and DOM Review Dimension Support in prompts.py & audit.py
- REQ-047: ai-review-plugin Surface Validation Compliance
"""
import os
import sys
import pytest
from pathlib import Path

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(PLUGIN_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from review.audit import (
    VERDICT_LEAK_FILES,
    assert_no_verdict_leaks,
    prepare_repo_sandbox,
    register_audit_parser,
)
from review.prompts import (
    DIMENSION_FOCUS_PROMPTS,
    build_review_prompt,
    build_audit_prompt,
)


# ============================================================================
# REQ-045: Sandbox Verdict Anti-Leak & Tripwire
# ============================================================================

class TestSandboxVerdictAntiLeak:
    def test_assert_no_verdict_leaks_clean_sandbox(self, tmp_path):
        sandbox = tmp_path / "clean_sandbox"
        sandbox.mkdir()
        (sandbox / "src").mkdir()
        (sandbox / "src" / "app.py").write_text("print('hello')\n")
        (sandbox / "docs").mkdir()
        (sandbox / "docs" / "spec.md").write_text("# Spec\n")

        # Must not raise
        assert_no_verdict_leaks(str(sandbox))

    @pytest.mark.parametrize("filename", sorted(VERDICT_LEAK_FILES))
    def test_assert_no_verdict_leaks_raises_on_leak_file(self, tmp_path, filename):
        sandbox = tmp_path / f"leak_{filename.replace('.', '_')}"
        sandbox.mkdir()
        leak_file = sandbox / filename
        leak_file.write_text("# Leaked findings\n")

        with pytest.raises(ValueError, match="Evaluator verdict leak in sandbox:"):
            assert_no_verdict_leaks(str(sandbox))

    def test_assert_no_verdict_leaks_raises_on_nested_leak_file(self, tmp_path):
        sandbox = tmp_path / "nested_sandbox"
        nested = sandbox / "docs" / "specs" / "feat-1"
        nested.mkdir(parents=True)
        (nested / "traceability_audit.json").write_text('{"verdict": "pass"}\n')

        with pytest.raises(ValueError, match="Evaluator verdict leak in sandbox:"):
            assert_no_verdict_leaks(str(sandbox))

    def test_assert_no_verdict_leaks_raises_on_review_round_pattern(self, tmp_path):
        sandbox = tmp_path / "round_sandbox"
        sandbox.mkdir()
        (sandbox / "review_round_1.md").write_text("# Prior Round\n")

        with pytest.raises(ValueError, match="Evaluator verdict leak in sandbox:"):
            assert_no_verdict_leaks(str(sandbox))

    def test_assert_no_verdict_leaks_allows_explicit_exceptions(self, tmp_path):
        sandbox = tmp_path / "allowed_sandbox"
        sandbox.mkdir()
        (sandbox / "review.md").write_text("# Target being reviewed\n")

        # When allowed_names includes review.md, it should not raise
        assert_no_verdict_leaks(str(sandbox), allowed_names=frozenset({"review.md"}))
        # Case variation support
        assert_no_verdict_leaks(str(sandbox), allowed_Names=frozenset({"review.md"}))

    def test_prepare_repo_sandbox_strips_all_verdict_leaks(self, tmp_path):
        repo = tmp_path / "source_repo"
        repo.mkdir()
        (repo / "src").mkdir()
        (repo / "src" / "main.py").write_text("print('core')\n")
        (repo / "review.md").write_text("prior review")
        (repo / "SELF_REVIEW.md").write_text("self review")
        (repo / "REVERIFICATION_REPORT.md").write_text("reverification report")
        (repo / "architecture_review.md").write_text("arch review")
        (repo / "review_round_1.md").write_text("round 1")
        (repo / "review_round_2.md").write_text("round 2")
        (repo / "docs").mkdir()
        (repo / "docs" / "traceability_audit.json").write_text("{}")

        work_dir = tmp_path / "work"
        work_dir.mkdir()

        repo_copy = prepare_repo_sandbox(str(repo), str(work_dir))
        assert os.path.exists(repo_copy)
        assert os.path.isfile(os.path.join(repo_copy, "src", "main.py"))

        # Verify all leak files were excluded/stripped
        for fname in VERDICT_LEAK_FILES:
            assert not os.path.exists(os.path.join(repo_copy, fname)), f"Found leaked file: {fname}"
        assert not os.path.exists(os.path.join(repo_copy, "review_round_1.md"))
        assert not os.path.exists(os.path.join(repo_copy, "review_round_2.md"))
        assert not os.path.exists(os.path.join(repo_copy, "docs", "traceability_audit.json"))

        # Tripwire check passes cleanly
        assert_no_verdict_leaks(repo_copy)

    def test_prepare_repo_sandbox_default_temp_dir(self, tmp_path):
        repo = tmp_path / "source_repo_default"
        repo.mkdir()
        (repo / "src").mkdir()
        (repo / "src" / "index.js").write_text("console.log('hi');\n")
        (repo / "review.md").write_text("leaked review\n")

        repo_copy = prepare_repo_sandbox(str(repo))
        try:
            assert os.path.exists(repo_copy)
            assert os.path.isfile(os.path.join(repo_copy, "src", "index.js"))
            assert not os.path.exists(os.path.join(repo_copy, "review.md"))
            assert_no_verdict_leaks(repo_copy)
        finally:
            import shutil
            parent_temp = os.path.dirname(repo_copy)
            if os.path.exists(parent_temp):
                shutil.rmtree(parent_temp)


# ============================================================================
# REQ-046: Orthogonal INV and DOM Review Dimension Support
# ============================================================================

class TestReviewDimensions:
    def test_build_review_prompt_dimension_all(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("def run(): pass\n")
        prompt = build_review_prompt(
            mode="code",
            target_copy=str(target),
            target_path=str(target),
            target_content="def run(): pass\n",
            dimension="all",
        )
        assert "Structural Invariants (INV)" not in prompt
        assert "Domain Completeness & Ergonomics (DOM)" not in prompt

    def test_build_review_prompt_dimension_inv(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("def run(): pass\n")
        prompt = build_review_prompt(
            mode="code",
            target_copy=str(target),
            target_path=str(target),
            target_content="def run(): pass\n",
            dimension="inv",
        )
        assert "Structural Invariants (INV)" in prompt
        assert "requirement ID traceability" in prompt
        assert "Domain Completeness & Ergonomics (DOM)" not in prompt

    def test_build_review_prompt_dimension_dom(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("def run(): pass\n")
        prompt = build_review_prompt(
            mode="code",
            target_copy=str(target),
            target_path=str(target),
            target_content="def run(): pass\n",
            dimension="dom",
        )
        assert "Domain Completeness & Ergonomics (DOM)" in prompt
        assert "domain edge cases" in prompt
        assert "Structural Invariants (INV)" not in prompt

    def test_build_audit_prompt_alias(self, tmp_path):
        target = tmp_path / "target.py"
        target.write_text("x = 1\n")
        p1 = build_review_prompt(
            mode="code", target_copy=str(target), target_path=str(target), target_content="x = 1\n", dimension="inv"
        )
        p2 = build_audit_prompt(
            mode="code", target_copy=str(target), target_path=str(target), target_content="x = 1\n", dimension="inv"
        )
        assert p1 == p2

    def test_register_audit_parser_dimension(self):
        parser = register_audit_parser()
        args_default = parser.parse_args(["--target", "/tmp/t", "--mode", "code", "--repo", "/tmp/r"])
        assert args_default.dimension == "all"

        args_inv = parser.parse_args(["--target", "/tmp/t", "--mode", "code", "--repo", "/tmp/r", "--dimension", "inv"])
        assert args_inv.dimension == "inv"

        args_dom = parser.parse_args(["--target", "/tmp/t", "--mode", "code", "--repo", "/tmp/r", "--dimension", "dom"])
        assert args_dom.dimension == "dom"

        with pytest.raises(SystemExit):
            parser.parse_args(["--target", "/tmp/t", "--mode", "code", "--repo", "/tmp/r", "--dimension", "invalid"])

    def test_file_line_counts_strictly_under_500(self):
        audit_path = os.path.join(SCRIPTS_DIR, "review", "audit.py")
        prompts_path = os.path.join(SCRIPTS_DIR, "review", "prompts.py")

        with open(audit_path, "r", encoding="utf-8") as f:
            audit_lines = len(f.readlines())
        with open(prompts_path, "r", encoding="utf-8") as f:
            prompts_lines = len(f.readlines())

        assert audit_lines < 500, f"audit.py exceeded 500 lines: {audit_lines}"
        assert prompts_lines < 500, f"prompts.py exceeded 500 lines: {prompts_lines}"


# ============================================================================
# REQ-047: ai-review-plugin Surface Validation Compliance
# ============================================================================

class TestSurfaceValidationCompliance:
    def test_rules_agents_content_and_budget(self):
        rules_path = os.path.join(PLUGIN_ROOT, "rules", "AGENTS.md")
        assert os.path.isfile(rules_path), "rules/AGENTS.md must exist in ai-review-plugin"

        with open(rules_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert len(content) < 2500, f"rules/AGENTS.md must be < 2500 chars, got {len(content)}"
        assert '<rule name="ai-review-governance">' in content
        assert "spec-review" in content
        assert "design-review" in content
        assert "code-review" in content

    def test_duplicate_skill_removed(self):
        dup_skill = os.path.join(PLUGIN_ROOT, "skills", "en-vi-book-translation-review")
        assert not os.path.exists(dup_skill), "Duplicate skill en-vi-book-translation-review must be removed from ai-review-plugin"

        global_dup = os.path.expanduser("~/.gemini/config/skills/en-vi-book-translation-review")
        assert not os.path.exists(global_dup), "Duplicate skill en-vi-book-translation-review must be removed from ~/.gemini/config/skills"

        canonical = os.path.expanduser("~/.gemini/config/plugins/agent-translator/skills/en-vi-book-translation-review")
        assert os.path.exists(canonical), "Canonical agent-translator skill must be preserved"

    def test_surface_validator_returns_valid_true(self):
        attention_guard_dir = os.path.expanduser("~/.gemini/config/plugins/attention-guard")
        validator_script = os.path.join(attention_guard_dir, "scripts", "surface_validator.py")
        assert os.path.isfile(validator_script), f"surface_validator.py missing at {validator_script}"

        sys.path.insert(0, os.path.join(attention_guard_dir, "scripts"))
        from surface_validator import validate_plugin_surface

        valid, errors, meta = validate_plugin_surface(PLUGIN_ROOT)
        assert valid is True, f"surface_validator failed with errors: {errors}"
        assert errors == []
        assert meta["always_on_chars"] <= meta["always_on_max"]
        assert "code-review" in meta["skills"]
        assert "design-review" in meta["skills"]
        assert "spec-review" in meta["skills"]
        assert "en-vi-book-translation-review" not in meta["skills"]
