#!/usr/bin/env python3
"""TDD suite for single-agent code-review collector and scoped linters (REQ-051..REQ-054)."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = PLUGIN_ROOT / "skills" / "code-review"
PREPARE_SCRIPT = SKILL_DIR / "scripts" / "prepare_code_review.py"
LINT_RUNNER_DIR = SKILL_DIR / "scripts"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_git_repo(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev User")


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_stub(bin_dir: Path, name: str, body: str) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / name
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_ac_051_1_uncommitted_staged_untracked_and_index_invariance(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    (repo / "app.py").write_text("def greet():\n    return 'hi'\n", encoding="utf-8")
    (repo / "Service.java").write_text("public class Service { int x = 1; }\n", encoding="utf-8")
    _git(repo, "add", "app.py", "Service.java")
    _git(repo, "commit", "-m", "baseline")

    # 1. Staged edit to app.py
    (repo / "app.py").write_text("def greet(items=[]):\n    return items\n", encoding="utf-8")
    _git(repo, "add", "app.py")

    # 2. Unstaged edit to Service.java
    (repo / "Service.java").write_text("public class Service { int x = 2; }\n", encoding="utf-8")

    # 3. Untracked worker.go
    (repo / "worker.go").write_text("package main\nfunc work() {}\n", encoding="utf-8")

    index_path = repo / ".git" / "index"
    status_before = _git(repo, "status", "--porcelain").stdout
    index_sha_before = _sha256_bytes(index_path)

    proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(repo), "--no-lint", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    bundle = json.loads(proc.stdout)

    assert _sha256_bytes(index_path) == index_sha_before
    assert _git(repo, "status", "--porcelain").stdout == status_before

    assert bundle["empty_diff"] is False
    assert set(bundle["changed_files"]) == {"app.py", "Service.java", "worker.go"}
    assert set(bundle["matched_rules"]) == {"python.md", "java.md", "go.md"}
    assert "Google Java Style" in bundle["language_rules_context"]
    assert "Effective Java" in bundle["language_rules_context"]
    assert "Google Go Style" in bundle["language_rules_context"]
    assert "Uber Go Style" in bundle["language_rules_context"]
    assert "PEP 8" in bundle["language_rules_context"]
    assert "app.py" in bundle["diff"]
    assert "Service.java" in bundle["diff"]
    assert "worker.go" in bundle["diff"]


def test_ac_051_1_staged_base_unborn_head_diff_file_and_codex_symlink(tmp_path: Path) -> None:
    # 1. --staged vs unstaged/untracked + --base HEAD~1
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "Service.java").write_text("class Service {}\n", encoding="utf-8")
    _git(repo, "add", "app.py", "Service.java")
    _git(repo, "commit", "-m", "c1")

    (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    _git(repo, "commit", "-m", "c2")

    # Add staged, unstaged, and untracked changes after c2
    (repo / "app.py").write_text("x = 3\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    (repo / "Service.java").write_text("class Service { int y = 1; }\n", encoding="utf-8")
    (repo / "worker.go").write_text("package main\n", encoding="utf-8")

    staged_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(repo), "--staged", "--no-lint", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    staged_bundle = json.loads(staged_proc.stdout)
    assert staged_bundle["changed_files"] == ["app.py"]
    assert staged_bundle["matched_rules"] == ["python.md"]

    base_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(repo), "--base", "HEAD~1", "--no-lint", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    base_bundle = json.loads(base_proc.stdout)
    assert set(base_bundle["changed_files"]) == {"app.py", "Service.java", "worker.go"}

    # 2. Unborn HEAD (zero commits + untracked init.py)
    unborn = tmp_path / "unborn"
    unborn.mkdir()
    _init_git_repo(unborn)
    (unborn / "init.py").write_text("def boot():\n    return True\n", encoding="utf-8")

    unborn_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(unborn), "--no-lint", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    unborn_bundle = json.loads(unborn_proc.stdout)
    assert unborn_bundle["empty_diff"] is False
    assert unborn_bundle["changed_files"] == ["init.py"]
    assert unborn_bundle["matched_rules"] == ["python.md"]
    assert _git(unborn, "status", "--porcelain").stdout == "?? init.py\n"

    # 3. --diff-file
    patch_file = tmp_path / "sample.patch"
    patch_file.write_text(
        "diff --git a/src/handler.ts b/src/handler.ts\n"
        "--- a/src/handler.ts\n"
        "+++ b/src/handler.ts\n"
        "@@ -1 +1 @@\n"
        "-export const ok = false;\n"
        "+export const ok = true;\n",
        encoding="utf-8",
    )
    patch_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--diff-file", str(patch_file), "--no-lint", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    patch_bundle = json.loads(patch_proc.stdout)
    assert patch_bundle["empty_diff"] is False
    assert patch_bundle["changed_files"] == ["src/handler.ts"]
    assert patch_bundle["matched_rules"] == ["ts_js_tsx_jsx.md"]

    # 4. Symlinked skill directory (~/.codex/skills/code-review style)
    codex_dir = tmp_path / ".codex" / "skills"
    codex_dir.mkdir(parents=True)
    symlink_skill = codex_dir / "code-review"
    symlink_skill.symlink_to(SKILL_DIR)

    symlink_proc = subprocess.run(
        [
            sys.executable,
            str(symlink_skill / "scripts" / "prepare_code_review.py"),
            "--repo",
            str(repo),
            "--no-lint",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    symlink_bundle = json.loads(symlink_proc.stdout)
    assert set(symlink_bundle["matched_rules"]) == {"python.md", "java.md", "go.md"}
    assert "Effective Java" in symlink_bundle["language_rules_context"]
    resolved_rule_docs = Path(symlink_skill / "scripts" / "prepare_code_review.py").resolve().parents[3] / "scripts" / "review" / "rules" / "rule_docs"
    assert len(list(resolved_rule_docs.glob("*.md"))) == 57


def test_ac_051_2_empty_diff_lockfiles_truncation_and_invalid_repo(tmp_path: Path) -> None:
    # 1. Clean repo -> empty_diff is True, exit 0
    clean_repo = tmp_path / "clean"
    clean_repo.mkdir()
    _init_git_repo(clean_repo)
    (clean_repo / "README.md").write_text("# Clean\n", encoding="utf-8")
    _git(clean_repo, "add", "README.md")
    _git(clean_repo, "commit", "-m", "init")

    clean_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(clean_repo), "--no-lint", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    clean_bundle = json.loads(clean_proc.stdout)
    assert clean_bundle["empty_diff"] is True
    assert clean_bundle["changed_files"] == []

    # 2. Lockfiles alongside src/lib.rs
    (clean_repo / "src").mkdir()
    (clean_repo / "src" / "lib.rs").write_text("pub fn add(a: i32, b: i32) -> i32 { a + b }\n", encoding="utf-8")
    (clean_repo / "package-lock.json").write_text('{"lockfileVersion": 3}\n', encoding="utf-8")
    (clean_repo / "Cargo.lock").write_text("version = 3\n", encoding="utf-8")
    (clean_repo / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    lock_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(clean_repo), "--no-lint", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    lock_bundle = json.loads(lock_proc.stdout)
    assert lock_bundle["empty_diff"] is False
    assert set(lock_bundle["skipped_lockfiles"]) == {"package-lock.json", "Cargo.lock", "uv.lock"}
    assert lock_bundle["changed_files"] == ["src/lib.rs"]
    assert lock_bundle["matched_rules"] == ["rust.md"]
    assert "package-lock.json" not in lock_bundle["diff"]
    assert "Cargo.lock" not in lock_bundle["diff"]
    assert "uv.lock" not in lock_bundle["diff"]
    assert "src/lib.rs" in lock_bundle["diff"]

    # 3. --max-diff-chars truncation
    (clean_repo / "src" / "lib.rs").write_text(
        "\n".join(f"pub fn f_{i}() -> i32 {{ {i} }}" for i in range(40)) + "\n",
        encoding="utf-8",
    )
    trunc_proc = subprocess.run(
        [
            sys.executable,
            str(PREPARE_SCRIPT),
            "--repo",
            str(clean_repo),
            "--no-lint",
            "--max-diff-chars",
            "200",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    trunc_bundle = json.loads(trunc_proc.stdout)
    assert trunc_bundle["diff_truncated"] is True
    assert len(trunc_bundle["diff"]) <= 200

    # 4. Invalid --repo and nonexistent --base ref leave zero agy_cr_idx_* temp files
    temp_root = Path(tempfile.gettempdir())
    before_idx = set(temp_root.glob("agy_cr_idx_*"))

    non_git = tmp_path / "not_a_repo"
    non_git.mkdir()
    bad_repo_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(non_git), "--no-lint", "--json"],
        capture_output=True,
        text=True,
    )
    assert bad_repo_proc.returncode != 0
    assert bad_repo_proc.stderr.strip()

    bad_ref_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(clean_repo), "--base", "bad-ref-xyz", "--no-lint", "--json"],
        capture_output=True,
        text=True,
    )
    assert bad_ref_proc.returncode != 0
    assert bad_ref_proc.stderr.strip()

    after_idx = set(temp_root.glob("agy_cr_idx_*"))
    assert after_idx == before_idx


def test_ac_052_1_and_ac_052_2_conventions_and_scoped_linters(tmp_path: Path) -> None:
    if str(LINT_RUNNER_DIR) not in sys.path:
        sys.path.insert(0, str(LINT_RUNNER_DIR))
    from lint_runner import discover_repo_conventions, parse_changed_lines, run_scoped_linters

    repo = tmp_path / "repo"
    repo.mkdir()
    _init_git_repo(repo)

    (repo / "go.mod").write_text("module example.com/app\n\ngo 1.23.2\n", encoding="utf-8")
    (repo / ".golangci.yml").write_text("run:\n  timeout: 2m\n", encoding="utf-8")
    (repo / "checkstyle.xml").write_text("<module name=\"Checker\"/>\n", encoding="utf-8")
    (repo / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    (repo / ".editorconfig").write_text("root = true\n", encoding="utf-8")
    (repo / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")
    (repo / "pom.xml").write_text("<project/>\n", encoding="utf-8")
    (repo / "Cargo.toml").write_text("[package]\nname = \"demo\"\n", encoding="utf-8")

    conventions = discover_repo_conventions(repo, ["app.py", "worker.go", "Service.java", "lib.rs"])
    assert conventions["go_version"] == "1.23.2"
    assert ".golangci.yml" in conventions["config_files"]
    assert "checkstyle.xml" in conventions["config_files"]
    assert "pyproject.toml" in conventions["config_files"]
    assert ".editorconfig" in conventions["config_files"]
    assert "CONTRIBUTING.md" in conventions["config_files"]
    assert "ruff" in conventions["python_tools"]

    # Baseline commit for git diff --check
    (repo / "app.py").write_text("import sys\n\ndef ok():\n    return 1\n", encoding="utf-8")
    (repo / "deploy.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    (repo / "worker.go").write_text("package main\nfunc w() {}\n", encoding="utf-8")
    (repo / "Service.java").write_text("class Service {}\n", encoding="utf-8")
    (repo / "lib.rs").write_text("pub fn x() {}\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")

    # Introduce trailing whitespace on line 2 of app.py and stage it so `git diff --check HEAD` is required
    (repo / "app.py").write_text("import sys\nimport os   \n\ndef ok():\n    return 1\n", encoding="utf-8")
    _git(repo, "add", "app.py")
    (repo / "deploy.sh").write_text("#!/bin/sh\necho $USER\n", encoding="utf-8")
    (repo / "worker.go").write_text("package main\nfunc w() { println(1) }\n", encoding="utf-8")
    (repo / "Service.java").write_text("class Service { int a = 1; }\n", encoding="utf-8")
    (repo / "lib.rs").write_text("pub fn x() -> i32 { 1 }\n", encoding="utf-8")

    diff_out = _git(repo, "diff", "HEAD", "--unified=3").stdout
    changed_lines = parse_changed_lines(diff_out)
    assert 2 in changed_lines["app.py"]
    assert 50 not in changed_lines["app.py"]

    bin_dir = tmp_path / "bin"
    _make_stub(
        bin_dir,
        "ruff",
        'echo "app.py:2:1: F401 unused import"\necho "app.py:50:1: E501 line too long"\nexit 1',
    )
    _make_stub(bin_dir, "shellcheck", "sleep 3\nexit 0")
    mvn_marker = tmp_path / "mvn_ran.txt"
    _make_stub(bin_dir, "mvn", f'echo "ran" > "{mvn_marker}"\nexit 0')
    cargo_marker = tmp_path / "cargo_ran.txt"
    _make_stub(bin_dir, "cargo", f'echo "ran" > "{cargo_marker}"\nexit 0')

    isolated_env = {"PATH": f"{bin_dir}:/usr/bin:/bin"}
    changed = ["app.py", "deploy.sh", "worker.go", "Service.java", "lib.rs"]

    lint_res = run_scoped_linters(
        repo,
        changed,
        changed_lines,
        deep_lint=False,
        timeout_sec=1,
        env=isolated_env,
    )

    findings = lint_res["findings"]
    assert any(f["tool"] == "git-diff-check" and f["file"] == "app.py" and f["in_diff_hunk"] is True for f in findings)
    assert any(f["tool"] == "ruff" and f["line"] == 2 and f["in_diff_hunk"] is True for f in findings)
    assert any(f["tool"] == "ruff" and f["line"] == 50 and f["in_diff_hunk"] is False for f in findings)

    skipped_joined = "\n".join(lint_res["skipped"])
    assert "shellcheck" in skipped_joined and "timed out" in skipped_joined
    assert "golangci-lint" in skipped_joined and "not installed" in skipped_joined
    assert not mvn_marker.exists()
    assert not cargo_marker.exists()

    # deep_lint=True executes mvn and cargo
    deep_res = run_scoped_linters(
        repo,
        ["Service.java", "lib.rs"],
        changed_lines,
        deep_lint=True,
        timeout_sec=2,
        env=isolated_env,
    )
    assert mvn_marker.exists()
    assert cargo_marker.exists()
    assert any("mvn" in item for item in deep_res["executed"])
    assert any("cargo" in item for item in deep_res["executed"])

    # Go linter branch coverage: golangci-lint present vs staticcheck fallback
    bin_go1 = tmp_path / "bin_go1"
    _make_stub(bin_go1, "golangci-lint", 'echo "worker.go:2:1: sample golangci issue"\nexit 1')
    go1_res = run_scoped_linters(
        repo,
        ["worker.go"],
        changed_lines,
        timeout_sec=2,
        env={"PATH": f"{bin_go1}:/usr/bin:/bin"},
    )
    assert any(f["tool"] == "golangci-lint" and f["in_diff_hunk"] is True for f in go1_res["findings"])

    bin_go2 = tmp_path / "bin_go2"
    _make_stub(bin_go2, "staticcheck", 'echo "worker.go:2:1: SA1000 sample staticcheck issue"\nexit 1')
    go2_res = run_scoped_linters(
        repo,
        ["worker.go"],
        changed_lines,
        timeout_sec=2,
        env={"PATH": f"{bin_go2}:/usr/bin:/bin"},
    )
    assert any(f["tool"] == "staticcheck" and f["in_diff_hunk"] is True for f in go2_res["findings"])
    assert any("golangci-lint" in s for s in go2_res["skipped"])

    # Default markdown CLI output with --dimension inv and active linters
    md_proc = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--repo", str(repo), "--dimension", "inv"],
        capture_output=True,
        text=True,
        env=isolated_env,
        check=True,
    )
    assert "Empty Diff: false" in md_proc.stdout
    assert "## Repo Conventions" in md_proc.stdout
    assert "## Scoped Linter Findings" in md_proc.stdout
    assert "## Dimension Focus" in md_proc.stdout
    assert "[IN_DIFF]" in md_proc.stdout
    assert "app.py:2" in md_proc.stdout
    assert "<language_review_rules>" in md_proc.stdout
    assert "<unified_diff>" in md_proc.stdout


def test_ac_053_and_ac_054_skill_and_rule_contracts() -> None:
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert "invoke_subagent" not in skill_text
    assert "peer_review.py" not in skill_text
    for line in skill_text.splitlines():
        if "docs/adr/" in line or "review.md" in line:
            assert "do not write" in line.lower()

    agents_text = (PLUGIN_ROOT / "rules" / "AGENTS.md").read_text(encoding="utf-8")
    assert "spec-review" in agents_text
    assert "design-review" in agents_text
    assert "code-review" in agents_text
    assert len(agents_text) <= 8000

    for script_path in (LINT_RUNNER_DIR / "lint_runner.py", PREPARE_SCRIPT):
        tree = ast.parse(script_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                for stmt in node.body:
                    assert not isinstance(stmt, ast.Pass), (
                        f"Forbidden ast.Pass in ExceptHandler of {script_path.name}:{stmt.lineno}"
                    )
