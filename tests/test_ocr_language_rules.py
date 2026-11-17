#!/usr/bin/env python3
"""Tests for Alibaba Open-Code-Review Language Rules & Glob Matcher (REQ-048, REQ-049, REQ-050)."""

import json
import sys
import unittest
from pathlib import Path

# Ensure scripts directory is on sys.path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from review.rule_matcher import (
        expand_braces,
        extract_diff_paths,
        match_doublestar,
        resolve_rules_for_paths,
        sniffs_as_objc,
    )
except ImportError:
    from scripts.review.rule_matcher import (
        expand_braces,
        extract_diff_paths,
        match_doublestar,
        resolve_rules_for_paths,
        sniffs_as_objc,
    )

try:
    from review.prompts import build_review_prompt
except ImportError:
    from scripts.review.prompts import build_review_prompt


class TestOcrLanguageRules(unittest.TestCase):
    """Test suite for REQ-048, REQ-049, and REQ-050."""

    @classmethod
    def setUpClass(cls):
        cls.rules_dir = SCRIPTS_DIR / "review" / "rules"
        cls.system_rules_path = cls.rules_dir / "system_rules.json"
        cls.rule_docs_dir = cls.rules_dir / "rule_docs"

    def test_req_048_vendored_rule_corpus(self):
        """AC-048-1: Verify system_rules.json and all 57 rule_docs/*.md files."""
        self.assertTrue(self.system_rules_path.is_file(), f"Missing {self.system_rules_path}")
        with open(self.system_rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("default_rule"), "default.md")
        path_rule_map = data.get("path_rule_map", {})
        self.assertEqual(len(path_rule_map), 58, f"Expected 58 path_rule_map entries, found {len(path_rule_map)}")

        self.assertTrue(self.rule_docs_dir.is_dir(), f"Missing {self.rule_docs_dir}")
        md_files = list(self.rule_docs_dir.glob("*.md"))
        self.assertEqual(len(md_files), 57, f"Expected 57 rule docs, found {len(md_files)}")
        for md in md_files:
            self.assertGreater(md.stat().st_size, 0, f"Rule doc {md.name} is empty")

    def test_req_049_specificity_and_brace_matching(self):
        """AC-049-1 & AC-049-2: Specificity ordering and brace expansion matching."""
        # Specificity: .github/workflows/ci.yml should resolve to github_workflows.md, not yaml.md
        rules = resolve_rules_for_paths([".github/workflows/ci.yml"])
        self.assertEqual([r[0] for r in rules], ["github_workflows.md"])

        # Specificity: src/dao/UserMapper.xml should resolve to mapper_dao_xml.md
        rules = resolve_rules_for_paths(["src/dao/UserMapper.xml"])
        self.assertEqual([r[0] for r in rules], ["mapper_dao_xml.md"])

        # Root and nested Go files: main.go, internal/agent/agent.go -> go.md
        rules = resolve_rules_for_paths(["main.go"])
        self.assertEqual([r[0] for r in rules], ["go.md"])
        rules = resolve_rules_for_paths(["internal/agent/agent.go"])
        self.assertEqual([r[0] for r in rules], ["go.md"])

        # TSX / JSX files: src/App.tsx -> ts_js_tsx_jsx.md
        rules = resolve_rules_for_paths(["src/App.tsx"])
        self.assertEqual([r[0] for r in rules], ["ts_js_tsx_jsx.md"])

        # Python files: scripts/review/prompts.py -> python.md
        rules = resolve_rules_for_paths(["scripts/review/prompts.py"])
        self.assertEqual([r[0] for r in rules], ["python.md"])

        # Gradle Kotlin DSL should resolve to build_gradle.md, not kotlin.md
        rules = resolve_rules_for_paths(["build.gradle.kts"])
        self.assertEqual([r[0] for r in rules], ["build_gradle.md"])
        rules = resolve_rules_for_paths(["app/build.gradle.kts"])
        self.assertEqual([r[0] for r in rules], ["build_gradle.md"])

        # Nested brace expansion
        expanded = expand_braces("**/*.{a,{b,c}}")
        self.assertEqual(expanded, ["**/*.a", "**/*.b", "**/*.c"])

        # Unknown extension: README.unknown -> default.md

    def test_req_049_objc_vs_matlab_sniffing(self):
        """AC-049-3: Objective-C vs MATLAB .m content sniffing."""
        # Objective-C: #import or // Header
        diff_objc_import = (
            "--- a/src/View.m\n"
            "+++ b/src/View.m\n"
            "@@ -0,0 +1,2 @@\n"
            "+#import <UIKit/UIKit.h>\n"
            "+@implementation View\n"
        )
        rules = resolve_rules_for_paths(["src/View.m"], diff_text=diff_objc_import)
        self.assertEqual([r[0] for r in rules], ["objc.md"])

        diff_objc_comment = (
            "--- a/src/View.m\n"
            "+++ b/src/View.m\n"
            "@@ -0,0 +1,2 @@\n"
            "+// Header comment for ObjC\n"
            "+#import <Foundation/Foundation.h>\n"
        )
        rules = resolve_rules_for_paths(["src/View.m"], diff_text=diff_objc_comment)
        self.assertEqual([r[0] for r in rules], ["objc.md"])

        # MATLAB: function y = f(x)
        diff_matlab = (
            "--- a/src/calc.m\n"
            "+++ b/src/calc.m\n"
            "@@ -0,0 +1,2 @@\n"
            "+function y = f(x)\n"
            "+y = x * 2;\n"
        )
        rules = resolve_rules_for_paths(["src/calc.m"], diff_text=diff_matlab)
        self.assertEqual([r[0] for r in rules], ["matlab.md"])

        # Sibling files in same diff must not cross-pollinate sniffing
        diff_sibling = (
            "diff --git a/src/View.m b/src/View.m\n"
            "--- a/src/View.m\n"
            "+++ b/src/View.m\n"
            "@@ -1,2 +1,2 @@\n"
            "+function y = f(x)\n"
            "+y = x * 2;\n"
            "diff --git a/src/MainView.m b/src/MainView.m\n"
            "--- a/src/MainView.m\n"
            "+++ b/src/MainView.m\n"
            "@@ -1,2 +1,2 @@\n"
            "+#import <UIKit/UIKit.h>\n"
            "+@implementation MainView\n"
        )
        rules = resolve_rules_for_paths(["src/View.m"], diff_text=diff_sibling)
        self.assertEqual([r[0] for r in rules], ["matlab.md"])
        rules = resolve_rules_for_paths(["src/MainView.m"], diff_text=diff_sibling)
        self.assertEqual([r[0] for r in rules], ["objc.md"])

    def test_req_049_deduplication_and_diff_extraction(self):
        """AC-049-4: Diff path extraction and deduplication."""
        diff_text = (
            "diff --git a/src/file1.go b/src/file1.go\n"
            "--- a/src/file1.go\n"
            "+++ b/src/file1.go\n"
            "@@ -1 +1 @@\n"
            "+package main\n"
            "diff --git a/dev/null b/src/new.py\n"
            "--- /dev/null\n"
            "+++ b/src/new.py\n"
            "@@ -0,0 +1 @@\n"
            "+print('hello')\n"
            "diff --git a/deleted.txt b/dev/null\n"
            "--- a/deleted.txt\n"
            "+++ /dev/null\n"
        )
        paths = extract_diff_paths(diff_text)
        self.assertEqual(paths, ["src/file1.go", "src/new.py"])

        # Hunk content or context lines must NOT be parsed as diff paths
        hunk_diff = (
            "diff --git a/doc.md b/doc.md\n"
            "--- a/doc.md\n"
            "+++ b/doc.md\n"
            "@@ -1 +1 @@\n"
            "++++ b/evil.py\n"
            " +++ b/other.py\n"
        )
        paths = extract_diff_paths(hunk_diff)
        self.assertEqual(paths, ["doc.md"])

        # Deduplication of rule bodies across multiple paths
        rules = resolve_rules_for_paths(["a.go", "b/c.go", "x.py", "y.py"])
        rule_names = [name for name, _ in rules]
        self.assertEqual(rule_names, ["go.md", "python.md"])

    def test_req_050_code_mode_prompt_injection(self):
        """AC-050-1 & AC-050-2: Injection into code-review prompt with Ground A/B guardrails."""
        diff_content = (
            "--- a/main.go\n"
            "+++ b/main.go\n"
            "@@ -1 +1 @@\n"
            "+func main() {}\n"
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1 +1 @@\n"
            "+def f(x=[]): pass\n"
        )

        prompt_code = build_review_prompt(
            mode="code",
            target_copy="target.file",
            target_path="diff.patch",
            target_content=diff_content,
        )

        self.assertIn("<language_review_rules>", prompt_code)
        self.assertIn("Go Review Principles", prompt_code)
        self.assertIn("Mutable Default Arguments", prompt_code)
        self.assertIn("Ground A", prompt_code)
        self.assertIn("Ground B", prompt_code)

        # mode="spec" and mode="design" must NOT inject <language_review_rules>
        prompt_spec = build_review_prompt(
            mode="spec",
            target_copy="target.file",
            target_path="diff.patch",
            target_content=diff_content,
        )
        self.assertNotIn("<language_review_rules>", prompt_spec)

        prompt_design = build_review_prompt(
            mode="design",
            target_copy="target.file",
            target_path="diff.patch",
            target_content=diff_content,
        )
        self.assertNotIn("<language_review_rules>", prompt_design)


if __name__ == "__main__":
    unittest.main()
