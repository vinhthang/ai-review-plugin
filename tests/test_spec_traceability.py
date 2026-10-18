#!/usr/bin/env python3
"""Continuous AST Specification Traceability Fitness Function (REQ-033).

Parses entrypoint Python scripts via AST to ensure 100% of CLI flags
map to explicit requirement IDs (REQ-xxx) in docs/specs/**/spec.md.
"""

import ast
import re
import unittest
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CLIArgumentVisitor(ast.NodeVisitor):
    """AST visitor that collects all flags from argparse.add_argument() calls."""

    def __init__(self, filename: str):
        self.filename = filename
        self.flags: List[Tuple[str, int, str]] = []

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith("-"):
                        self.flags.append((arg.value, node.lineno, self.filename))
        self.generic_visit(node)


def extract_cli_flags_from_file(file_path: Path) -> List[Tuple[str, int, str]]:
    """Parse a Python file using AST and return all flags from add_argument."""
    content = file_path.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(file_path))
    visitor = CLIArgumentVisitor(file_path.name)
    visitor.visit(tree)
    return visitor.flags


def extract_spec_requirement_mappings(specs_dir: Path) -> Dict[str, Set[str]]:
    """Extract mappings from CLI flags (--flag) to requirement IDs (REQ-xxx).

    Scans all specification files in docs/specs/**/spec.md.
    """
    flag_to_reqs: Dict[str, Set[str]] = {}
    spec_files = list(specs_dir.glob("**/spec.md")) + list(specs_dir.glob("*.md"))

    for spec_file in spec_files:
        content = spec_file.read_text(encoding="utf-8")

        # Split content into sections by headers (## or ###)
        sections = re.split(r"\n(?=#{1,4}\s+)", content)
        for section in sections:
            # Find requirement IDs in this section
            req_matches = re.findall(r"\b(REQ-[0-9A-Za-z_-]+)\b", section)
            if not req_matches:
                continue

            # Find all CLI flags mentioned in this section
            flags = re.findall(r"(--[a-zA-Z0-9_-]+)", section)
            for flag in flags:
                if flag not in flag_to_reqs:
                    flag_to_reqs[flag] = set()
                flag_to_reqs[flag].update(req_matches)

    return flag_to_reqs


class TestSpecTraceability(unittest.TestCase):
    """Continuous AST Specification Traceability Fitness Function."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.scripts_dir = self.repo_root / "scripts"
        self.specs_dir = self.repo_root / "docs" / "specs"

    def test_entrypoint_scripts_cli_traceability(self):
        """Assert 100% of CLI flags in entrypoint scripts map to documented REQ-xxx."""
        entrypoint_scripts = list(self.scripts_dir.glob("*.py"))
        self.assertTrue(len(entrypoint_scripts) > 0, "No entrypoint scripts found in scripts/")

        spec_mappings = extract_spec_requirement_mappings(self.specs_dir)
        untraced_flags = []

        for script in entrypoint_scripts:
            flags = extract_cli_flags_from_file(script)
            for flag_name, line_no, filename in flags:
                # Discard short aliases like -h or check long flags
                if flag_name.startswith("--"):
                    if flag_name not in spec_mappings or not spec_mappings[flag_name]:
                        untraced_flags.append({
                            "flag": flag_name,
                            "line": line_no,
                            "file": filename,
                        })

        self.assertEqual(
            len(untraced_flags),
            0,
            f"Orphaned CLI flags detected without governing REQ-xxx in docs/specs/:\n{untraced_flags}",
        )

    def test_detects_untracked_flag_ast(self):
        """Verify fitness function flags undocumented arguments as violations."""
        dummy_code = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--untracked-test-flag", help="Undocumented")
"""
        tree = ast.parse(dummy_code, filename="dummy.py")
        visitor = CLIArgumentVisitor("dummy.py")
        visitor.visit(tree)

        spec_mappings = extract_spec_requirement_mappings(self.specs_dir)
        flag_name = visitor.flags[0][0]
        self.assertNotIn(flag_name, spec_mappings)

    def test_ast_visitor_flag_extraction(self):
        """Verify CLIArgumentVisitor extracts both short and long flags."""
        sample_code = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-w", "--workspace", default=".", help="Workspace")
parser.add_argument("--json", action="store_true")
"""
        tree = ast.parse(sample_code)
        visitor = CLIArgumentVisitor("sample.py")
        visitor.visit(tree)

        extracted = [f[0] for f in visitor.flags]
        self.assertIn("-w", extracted)
        self.assertIn("--workspace", extracted)
        self.assertIn("--json", extracted)


if __name__ == "__main__":
    unittest.main()
