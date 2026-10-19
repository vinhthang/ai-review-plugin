"""Unit tests for Codebase Simplification, Deduplication & Sub-500-Line Modularization (REQ-041 - REQ-044)."""
import os
import tempfile
from pathlib import Path
import pytest

from review.models import ISSUE_DESCRIPTION_FALLBACK_KEYS, extract_issue_description
from review.prompts import build_adr_context, build_review_prompt, load_diagnostic_text, load_prior_review_text
from review.runners.cdp_client import CDPClient as CDPClientDirect
from review.runners.edge_applescript_runner import CDPClient as CDPClientReexported
from review.governance import update_index_catalog


class TestExtractIssueDescription:
    """Test extract_issue_description behavior across fallback keys (REQ-044)."""

    def test_extract_empty_and_whitespace(self):
        assert extract_issue_description({}) == ""
        assert extract_issue_description({"description": "   "}) == ""
        assert extract_issue_description({"description": None}) == ""

    def test_extract_primary_description(self):
        item = {"description": "Primary issue description", "details": "Alternative"}
        assert extract_issue_description(item) == "Primary issue description"

    def test_extract_all_fallback_keys(self):
        for key in ISSUE_DESCRIPTION_FALLBACK_KEYS:
            item = {key: f"Value for {key}"}
            assert extract_issue_description(item) == f"Value for {key}", f"Failed for key {key}"

    def test_extract_priority_order(self):
        # Earlier keys in tuple take precedence over later keys
        item = {
            "summary": "Summary text",
            "comment": "Comment text",
            "note": "Note text",
        }
        assert extract_issue_description(item) == "Summary text"

    def test_extract_skips_empty_fallbacks(self):
        item = {
            "description": "",
            "details": "   ",
            "message": None,
            "summary": "First valid text",
        }
        assert extract_issue_description(item) == "First valid text"


class TestPromptsModularization:
    """Test build_review_prompt and prompt helpers in review.prompts (REQ-042)."""

    def test_build_review_prompt_spec_mode(self):
        prompt = build_review_prompt(
            mode="spec",
            target_copy="/tmp/target.file",
            target_path="/repo/spec.md",
            target_content="# My Spec\nREQ-001",
        )
        assert "Perform a spec review of this file: /tmp/target.file" in prompt
        assert "Evaluate against the Build-Ready Specification Standard" in prompt
        assert "1. Consequential ambiguity" in prompt
        assert "<target_artifact path=\"spec.md\">" in prompt

    def test_build_review_prompt_design_mode_with_spec(self):
        prompt = build_review_prompt(
            mode="design",
            target_copy="/tmp/target.file",
            target_path="/repo/design.md",
            target_content="# My Design",
            spec_path="/repo/spec.md",
            spec_content="# Spec Content",
            spec_copy="/tmp/spec.file",
            has_spec=True,
        )
        assert "Perform a design review of this file: /tmp/target.file" in prompt
        assert "Governing Specification: Compare this plan against the specification at /tmp/spec.file" in prompt
        assert "<governing_specification path=\"spec.md\">" in prompt
        assert "docs/specs/" in prompt

    def test_build_review_prompt_design_mode_standalone(self):
        prompt = build_review_prompt(
            mode="design",
            target_copy="/tmp/target.file",
            target_path="/repo/design.md",
            target_content="# Standalone Design",
            has_spec=False,
        )
        assert "Standalone Design Review: No governing specification was provided" in prompt
        assert "docs/specs/" not in prompt

    def test_build_review_prompt_code_mode(self):
        prompt = build_review_prompt(
            mode="code",
            target_copy="/tmp/target.file",
            target_path="/repo/main.py",
            target_content="print('hello')",
        )
        assert "Perform a code review of this file: /tmp/target.file" in prompt
        assert "Focus on code-level issues, logic, and correctness." in prompt
        assert "Documentation vs Code Guardrail" in prompt

    def test_build_review_prompt_context_embedding(self):
        prompt = build_review_prompt(
            mode="code",
            target_copy="/tmp/target.file",
            target_path="/repo/main.py",
            target_content="code",
            adr_content="ADR Content Here",
            prior_review_text='[{"severity": "P1", "description": "Prior issue"}]',
            diagnostic_text="Failure trace here",
            message="Please pay extra attention to memory leaks.",
        )
        assert "<architectural_decision_records>\nADR Content Here\n</architectural_decision_records>" in prompt
        assert "<prior_review_context>" in prompt
        assert "<diagnostic_context>\nFailure trace here\n</diagnostic_context>" in prompt
        assert "Message: Please pay extra attention to memory leaks." in prompt


class TestCDPClientExtraction:
    """Test CDPClient extraction and re-export compatibility (REQ-043)."""

    def test_cdp_client_identity_and_methods(self):
        assert CDPClientDirect is CDPClientReexported
        assert hasattr(CDPClientDirect, "is_available")
        assert hasattr(CDPClientDirect, "find_gemini_tab")
        assert hasattr(CDPClientDirect, "open_gemini_tab")
        assert hasattr(CDPClientDirect, "execute_js")


class TestGovernanceEscapedPipes:
    """Test table parsing with escaped pipes in update_index_catalog (REQ-041, REQ-043)."""

    def test_update_index_catalog_with_escaped_pipe(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            specs_dir = Path(tmp_dir) / "docs" / "specs"
            specs_dir.mkdir(parents=True)
            index_path = specs_dir / "INDEX.md"

            table_content = (
                "# Specifications\n\n"
                "| Feature ID | Title | Status | Requirements | Key Decisions | Specification Path |\n"
                "|:---|:---|:---|:---|:---|:---|\n"
                "| `feat-escaped` | Title with \\| escaped pipe | Planning | `REQ-001` | `ADR-001` | [Spec](feat-escaped/spec.md) |\n"
            )
            index_path.write_text(table_content, encoding="utf-8")

            success = update_index_catalog(
                repo_root=tmp_dir,
                feature_id="feat-escaped",
                status="Approved",
                review_link="feat-escaped/reviews/design-v1.json",
            )
            assert success is True

            updated = index_path.read_text(encoding="utf-8")
            assert "Approved" in updated
            assert "Title with \\| escaped pipe" in updated
            assert "[Spec](feat-escaped/reviews/design-v1.json)" in updated


class TestSub500LineLimits:
    """Verify that all Python files in scripts/ are strictly under 500 lines (REQ-042, REQ-043)."""

    def test_all_scripts_under_500_lines(self):
        repo_root = Path(__file__).resolve().parent.parent
        scripts_dir = repo_root / "scripts"
        py_files = list(scripts_dir.rglob("*.py"))
        assert len(py_files) > 0, "No python scripts found in scripts/"

        violations = []
        for p in py_files:
            line_count = len(p.read_text(encoding="utf-8").splitlines())
            if line_count >= 500:
                violations.append(f"{p.relative_to(repo_root)}: {line_count} lines (>= 500)")

        assert not violations, f"Files exceeding 500-line AST gate limit: {violations}"

    def test_modularized_targets_under_360_lines(self):
        repo_root = Path(__file__).resolve().parent.parent
        targets = [
            repo_root / "scripts" / "review" / "audit.py",
            repo_root / "scripts" / "review" / "prompts.py",
            repo_root / "scripts" / "review" / "runners" / "edge_applescript_runner.py",
            repo_root / "scripts" / "review" / "runners" / "cdp_client.py",
        ]
        violations = []
        for p in targets:
            assert p.is_file(), f"Target file does not exist: {p}"
            line_count = len(p.read_text(encoding="utf-8").splitlines())
            if line_count >= 360:
                violations.append(f"{p.relative_to(repo_root)}: {line_count} lines (>= 360)")

        assert not violations, f"Modularized targets exceeding 360-line limit: {violations}"


class TestResolvePackageDir:
    """Test resolve_package_dir single signature (REQ-013)."""

    def test_resolve_package_dir_valid(self, tmp_path):
        from spec_checker import resolve_package_dir

        specs_dir = tmp_path / "docs" / "specs"
        pkg_dir = specs_dir / "feat-x"
        pkg_dir.mkdir(parents=True)

        spec = {"feature_id": "feat-x", "spec_path": "./feat-x/spec.md"}
        resolved, err = resolve_package_dir(spec, tmp_path, specs_dir)
        assert err is None
        assert resolved == pkg_dir.resolve()

