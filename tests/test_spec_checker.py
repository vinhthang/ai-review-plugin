#!/usr/bin/env python3
"""Unit tests for Shared Specification Verification Engine (REQ-032)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from spec_checker import (
    get_active_specifications,
    parse_specs_index,
    validate_spec_package,
    verify_active_specification,
)


class TestSpecChecker(unittest.TestCase):
    """Test suite for spec_checker.py."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.workspace = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_valid_active_specification_live_workspace(self):
        """Verify the actual project workspace has a valid active spec."""
        repo_root = Path(__file__).resolve().parent.parent
        res = verify_active_specification(repo_root)
        self.assertTrue(res.get("valid"))
        self.assertEqual(res.get("status"), "valid")
        self.assertIn("2026-10-09-spec-gate-enforcement", res.get("active_features", []))

    def test_no_spec_framework(self):
        """Workspace without docs/specs returns no_spec_framework and valid=True."""
        res = verify_active_specification(self.workspace)
        self.assertTrue(res.get("valid"))
        self.assertEqual(res.get("status"), "no_spec_framework")

    def test_missing_index(self):
        """Workspace with docs/specs but missing INDEX.md returns status=invalid."""
        specs_dir = self.workspace / "docs" / "specs"
        specs_dir.mkdir(parents=True)
        res = verify_active_specification(self.workspace)
        self.assertFalse(res.get("valid"))
        self.assertEqual(res.get("status"), "invalid")
        self.assertIn("Missing docs/specs/INDEX.md", res.get("reason", ""))

    def test_index_only_completed_features(self):
        """INDEX.md with only Completed features returns no_active_spec."""
        specs_dir = self.workspace / "docs" / "specs"
        specs_dir.mkdir(parents=True)
        index_file = specs_dir / "INDEX.md"
        index_file.write_text(
            "| Feature ID | Title | Status | REQ Range | Key Decisions | Spec Path |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| `feat-1` | Feature One | Completed | `REQ-001` | ADR | `./feat-1/spec.md` |\n",
            encoding="utf-8",
        )
        res = verify_active_specification(self.workspace)
        self.assertFalse(res.get("valid"))
        self.assertEqual(res.get("status"), "no_active_spec")

    def test_incomplete_package_missing_required_files(self):
        """Active spec missing design.md or decisions.md returns incomplete_package."""
        specs_dir = self.workspace / "docs" / "specs"
        feat_dir = specs_dir / "feat-2"
        feat_dir.mkdir(parents=True)
        (feat_dir / "spec.md").write_text("# Spec\nREQ-001: Testing requirement\n", encoding="utf-8")
        # Missing decisions.md and design.md

        index_file = specs_dir / "INDEX.md"
        index_file.write_text(
            "| Feature ID | Title | Status | REQ Range | Key Decisions | Spec Path |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| `feat-2` | Feature Two | In-Progress | `REQ-001` | ADR | `./feat-2/spec.md` |\n",
            encoding="utf-8",
        )

        res = verify_active_specification(self.workspace)
        self.assertFalse(res.get("valid"))
        self.assertEqual(res.get("status"), "incomplete_package")
        self.assertEqual(res.get("feature_id"), "feat-2")
        self.assertIn("Missing required specification file", res.get("reason", ""))

    def test_incomplete_package_empty_file(self):
        """Active spec with an empty file returns incomplete_package."""
        specs_dir = self.workspace / "docs" / "specs"
        feat_dir = specs_dir / "feat-3"
        feat_dir.mkdir(parents=True)
        (feat_dir / "spec.md").write_text("# Spec\nREQ-001: Testing requirement\n", encoding="utf-8")
        (feat_dir / "decisions.md").write_text("", encoding="utf-8")  # Empty!
        (feat_dir / "design.md").write_text("# Design\nBlueprint content\n", encoding="utf-8")

        index_file = specs_dir / "INDEX.md"
        index_file.write_text(
            "| Feature ID | Title | Status | REQ Range | Key Decisions | Spec Path |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| `feat-3` | Feature Three | Planning | `REQ-001` | ADR | `./feat-3/spec.md` |\n",
            encoding="utf-8",
        )

        res = verify_active_specification(self.workspace)
        self.assertFalse(res.get("valid"))
        self.assertEqual(res.get("status"), "incomplete_package")
        self.assertIn("empty", res.get("reason", "").lower())

    def test_incomplete_package_missing_req_identifier(self):
        """spec.md without any REQ/FLOW/ALIGN pattern returns incomplete_package."""
        specs_dir = self.workspace / "docs" / "specs"
        feat_dir = specs_dir / "feat-4"
        feat_dir.mkdir(parents=True)
        (feat_dir / "spec.md").write_text("# Spec\nNo requirement pattern here!\n", encoding="utf-8")
        (feat_dir / "decisions.md").write_text("# Decisions\nContent\n", encoding="utf-8")
        (feat_dir / "design.md").write_text("# Design\nBlueprint content\n", encoding="utf-8")

        index_file = specs_dir / "INDEX.md"
        index_file.write_text(
            "| Feature ID | Title | Status | REQ Range | Key Decisions | Spec Path |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| `feat-4` | Feature Four | Draft | `REQ-001` | ADR | `./feat-4/spec.md` |\n",
            encoding="utf-8",
        )

        res = verify_active_specification(self.workspace)
        self.assertFalse(res.get("valid"))
        self.assertEqual(res.get("status"), "incomplete_package")
        self.assertIn("requirement pattern", res.get("reason", "").lower())

    def test_cli_execution_exit_codes(self):
        """Test CLI execution across success and failure exit codes."""
        checker_script = SCRIPTS_DIR / "spec_checker.py"
        repo_root = Path(__file__).resolve().parent.parent

        # 1. Exit code 0 on valid workspace
        cmd_valid = [sys.executable, str(checker_script), "--workspace", str(repo_root), "--json"]
        proc_valid = subprocess.run(cmd_valid, capture_output=True, text=True)
        self.assertEqual(proc_valid.returncode, 0)
        data = json.loads(proc_valid.stdout)
        self.assertTrue(data.get("valid"))

        # 2. Exit code 1 on workspace with only completed features
        specs_dir = self.workspace / "docs" / "specs"
        specs_dir.mkdir(parents=True)
        index_file = specs_dir / "INDEX.md"
        index_file.write_text(
            "| Feature ID | Title | Status | REQ Range | Key Decisions | Spec Path |\n"
            "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
            "| `feat-1` | Feature One | Completed | `REQ-001` | ADR | `./feat-1/spec.md` |\n",
            encoding="utf-8",
        )
        cmd_invalid = [sys.executable, str(checker_script), "--workspace", str(self.workspace), "--json"]
        proc_invalid = subprocess.run(cmd_invalid, capture_output=True, text=True)
        self.assertEqual(proc_invalid.returncode, 1)
        data_invalid = json.loads(proc_invalid.stdout)
        self.assertFalse(data_invalid.get("valid"))
        self.assertEqual(data_invalid.get("status"), "no_active_spec")

        # 3. Quiet flag suppresses stdout
        cmd_quiet = [sys.executable, str(checker_script), "--workspace", str(repo_root), "--quiet"]
        proc_quiet = subprocess.run(cmd_quiet, capture_output=True, text=True)
        self.assertEqual(proc_quiet.returncode, 0)
        self.assertEqual(proc_quiet.stdout.strip(), "")

    def test_resolve_package_dir(self):
        """Test single-signature resolve_package_dir (REQ-013)."""
        from spec_checker import resolve_package_dir
        specs_dir = self.workspace / "docs" / "specs"
        pkg_dir = specs_dir / "my-feature"
        pkg_dir.mkdir(parents=True)

        spec_dict = {"feature_id": "my-feature", "spec_path": "./my-feature/spec.md"}
        resolved, err = resolve_package_dir(spec_dict, self.workspace, specs_dir)
        self.assertIsNone(err)
        self.assertEqual(resolved, pkg_dir.resolve())


if __name__ == "__main__":
    unittest.main()
