#!/usr/bin/env python3
"""Read-only diff, convention, linter, and language-rule collector for single-agent code-review (REQ-051)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PLUGIN_ROOT = Path(__file__).resolve().parents[3]

for path_entry in (str(SCRIPT_DIR), str(PLUGIN_ROOT / "scripts")):
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)

from lint_runner import discover_repo_conventions, parse_changed_lines, run_scoped_linters
from review.prompts import DIMENSION_FOCUS_PROMPTS
from review.rule_matcher import (
    build_language_rules_context,
    extract_diff_paths,
    resolve_rules_for_paths,
)

GIT_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
LOCKFILE_BASENAMES: frozenset[str] = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "cargo.lock",
        "poetry.lock",
        "uv.lock",
        "go.sum",
        "composer.lock",
        "gemfile.lock",
        "package.resolved",
        "podfile.lock",
        "gradle.lockfile",
    }
)


def _run_git(repo_root: Path, args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )


def _ensure_git_repo(repo_root: Path) -> None:
    if not repo_root.is_dir():
        raise ValueError(f"Repository directory does not exist: {repo_root}")
    probe = _run_git(repo_root, ["rev-parse", "--is-inside-work-tree"])
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        detail = probe.stderr.strip() or "not a git repository"
        raise ValueError(f"Invalid git repository '{repo_root}': {detail}")


def _capture_diff_with_temp_index(
    repo_root: Path,
    compare_ref: str | None,
    paths: list[str],
) -> str:
    head_probe = _run_git(repo_root, ["rev-parse", "--verify", "HEAD"])
    head_exists = head_probe.returncode == 0
    target_ref = compare_ref if compare_ref is not None else ("HEAD" if head_exists else GIT_EMPTY_TREE)

    fd, tmp_idx = tempfile.mkstemp(prefix="agy_cr_idx_")
    os.close(fd)
    os.unlink(tmp_idx)
    child_env = {**os.environ, "GIT_INDEX_FILE": tmp_idx}

    try:
        if head_exists:
            rt_proc = _run_git(repo_root, ["read-tree", "HEAD"], env=child_env)
            if rt_proc.returncode != 0:
                raise RuntimeError(f"git read-tree HEAD failed: {rt_proc.stderr.strip()}")

        add_targets = paths if paths else ["."]
        add_proc = _run_git(repo_root, ["add", "-A", "--", *add_targets], env=child_env)
        if add_proc.returncode != 0:
            raise RuntimeError(f"git add into temporary index failed: {add_proc.stderr.strip()}")

        diff_cmd = ["diff", "--cached", "--no-color", "--unified=3", target_ref]
        if paths:
            diff_cmd.extend(["--", *paths])
        diff_proc = _run_git(repo_root, diff_cmd, env=child_env)
        if diff_proc.returncode != 0:
            raise RuntimeError(f"git diff failed: {diff_proc.stderr.strip()}")
        return diff_proc.stdout
    finally:
        Path(tmp_idx).unlink(missing_ok=True)


def _capture_raw_diff(
    repo_root: Path | None,
    *,
    staged: bool = False,
    base: str | None = None,
    diff_file: Path | None = None,
    paths: list[str] | None = None,
) -> str:
    path_list = paths or []
    if diff_file is not None:
        if not diff_file.is_file():
            raise ValueError(f"Diff file not found: {diff_file}")
        return diff_file.read_text(encoding="utf-8", errors="replace")

    if repo_root is None:
        raise ValueError("Repository root is required when --diff-file is not specified")
    _ensure_git_repo(repo_root)

    if staged:
        cmd = ["diff", "--cached", "--no-color", "--unified=3"]
        if path_list:
            cmd.extend(["--", *path_list])
        proc = _run_git(repo_root, cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"git diff --cached failed: {proc.stderr.strip()}")
        return proc.stdout

    if base is not None:
        verify = _run_git(repo_root, ["rev-parse", "--verify", base])
        if verify.returncode != 0:
            raise ValueError(f"Invalid --base reference '{base}': {verify.stderr.strip() or 'unknown revision'}")
        return _capture_diff_with_temp_index(repo_root, compare_ref=base, paths=path_list)

    return _capture_diff_with_temp_index(repo_root, compare_ref=None, paths=path_list)


def _split_diff_sections(raw_diff: str) -> list[str]:
    if not raw_diff.strip():
        return []
    lines = raw_diff.splitlines(keepends=True)
    has_git_headers = any(line.startswith("diff --git ") for line in lines)
    sections: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        is_boundary = line.startswith("diff --git ") if has_git_headers else line.startswith("--- ")
        if is_boundary and current:
            sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)

    return ["".join(sec) for sec in sections]


def filter_lockfile_sections(raw_diff: str) -> tuple[str, list[str]]:
    """Strip lockfile diff sections from unified diff text while recording skipped paths."""
    kept_sections: list[str] = []
    skipped_lockfiles: list[str] = []
    seen_skipped: set[str] = set()

    for section in _split_diff_sections(raw_diff):
        sec_paths = extract_diff_paths(section)
        if sec_paths and all(Path(p).name.lower() in LOCKFILE_BASENAMES for p in sec_paths):
            for p in sec_paths:
                if p not in seen_skipped:
                    seen_skipped.add(p)
                    skipped_lockfiles.append(p)
            continue
        kept_sections.append(section)

    return "".join(kept_sections), skipped_lockfiles


def collect_review_bundle(
    *,
    repo: str | Path = ".",
    staged: bool = False,
    base: str | None = None,
    diff_file: str | Path | None = None,
    no_lint: bool = False,
    deep_lint: bool = False,
    dimension: str = "all",
    max_diff_chars: int = 120_000,
    paths: list[str] | None = None,
) -> dict[str, Any]:
    """Collect unified diff, conventions, scoped linter output, and language review rules."""
    diff_path = Path(diff_file).resolve() if diff_file is not None else None
    repo_root = Path(repo).resolve() if diff_path is None else None

    raw_diff = _capture_raw_diff(
        repo_root,
        staged=staged,
        base=base,
        diff_file=diff_path,
        paths=paths,
    )
    filtered_diff, skipped_lockfiles = filter_lockfile_sections(raw_diff)
    changed_files = extract_diff_paths(filtered_diff)
    empty_diff = not changed_files and not filtered_diff.strip()

    rules_dir = str(PLUGIN_ROOT / "scripts" / "review" / "rules")
    if changed_files:
        matched_pairs = resolve_rules_for_paths(changed_files, diff_text=filtered_diff, rules_dir=rules_dir)
        matched_rules = [name for name, _ in matched_pairs]
        language_rules_context = build_language_rules_context(filtered_diff, rules_dir=rules_dir)
    else:
        matched_rules = []
        language_rules_context = ""

    if repo_root is not None:
        repo_conventions = discover_repo_conventions(repo_root, changed_files)
    else:
        repo_conventions = {
            "config_files": [],
            "go_version": None,
            "python_tools": [],
            "java_configs": {},
            "deep_lint_hints": [],
        }

    if empty_diff or repo_root is None or no_lint:
        reason = "linters skipped (--no-lint)" if no_lint else "linters skipped (no changed files or diff-file mode)"
        linters: dict[str, Any] = {"findings": [], "executed": [], "skipped": [reason]}
    else:
        changed_lines = parse_changed_lines(filtered_diff)
        linters = run_scoped_linters(repo_root, changed_files, changed_lines, deep_lint=deep_lint)

    diff_truncated = len(filtered_diff) > max_diff_chars
    diff_output = filtered_diff[:max_diff_chars] if diff_truncated else filtered_diff

    return {
        "empty_diff": empty_diff,
        "changed_files": changed_files,
        "skipped_lockfiles": skipped_lockfiles,
        "matched_rules": matched_rules,
        "repo_conventions": repo_conventions,
        "linters": linters,
        "dimension": dimension,
        "language_rules_context": language_rules_context,
        "diff": diff_output,
        "diff_truncated": diff_truncated,
    }


def format_bundle_markdown(bundle: dict[str, Any]) -> str:
    """Format collected review bundle into readable Markdown/XML context for single-agent review."""
    lines = [
        f"Empty Diff: {'true' if bundle['empty_diff'] else 'false'}",
        f"Changed Files ({len(bundle['changed_files'])}): {', '.join(bundle['changed_files']) or 'none'}",
        f"Skipped Lockfiles: {', '.join(bundle['skipped_lockfiles']) or 'none'}",
        f"Matched Rules: {', '.join(bundle['matched_rules']) or 'none'}",
        f"Dimension: {bundle['dimension']}",
        "",
        "## Repo Conventions",
        json.dumps(bundle["repo_conventions"], indent=2),
        "",
        "## Scoped Linter Findings",
        f"Executed: {', '.join(bundle['linters']['executed']) or 'none'}",
        f"Skipped: {', '.join(bundle['linters']['skipped']) or 'none'}",
    ]
    for finding in bundle["linters"]["findings"]:
        tag = "IN_DIFF" if finding["in_diff_hunk"] else "OUTSIDE_DIFF"
        loc = f"{finding['file']}:{finding['line']}" if finding["line"] is not None else finding["file"]
        lines.append(f"- [{tag}] ({finding['tool']}) {loc}: {finding['message']}")

    dim_prompt = DIMENSION_FOCUS_PROMPTS.get(bundle["dimension"], "")
    if dim_prompt:
        lines.extend(["", "## Dimension Focus", dim_prompt.strip()])

    if bundle["language_rules_context"]:
        lines.extend(["", bundle["language_rules_context"]])

    if bundle["diff"]:
        lines.extend(["", "<unified_diff>", bundle["diff"].rstrip("\n"), "</unified_diff>"])
        if bundle["diff_truncated"]:
            lines.append("Note: Unified diff was truncated to --max-diff-chars.")

    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare read-only single-agent code review context.")
    parser.add_argument("--repo", default=".", help="Path to git repository (default: .)")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--staged", action="store_true", help="Review staged index changes only")
    mode_group.add_argument("--base", help="Compare working tree against base git ref")
    mode_group.add_argument("--diff-file", help="Read unified diff from an existing patch file")
    parser.add_argument("--no-lint", action="store_true", help="Skip local scoped CLI linters")
    parser.add_argument("--deep-lint", action="store_true", help="Include slower build-tool linters (mvn/gradle/cargo)")
    parser.add_argument("--dimension", choices=("all", "inv", "dom"), default="all", help="Review dimension focus")
    parser.add_argument("--max-diff-chars", type=int, default=120_000, help="Maximum unified diff characters")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON bundle")
    parser.add_argument("paths", nargs="*", help="Optional path filters")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        bundle = collect_review_bundle(
            repo=args.repo,
            staged=args.staged,
            base=args.base,
            diff_file=args.diff_file,
            no_lint=args.no_lint,
            deep_lint=args.deep_lint,
            dimension=args.dimension,
            max_diff_chars=args.max_diff_chars,
            paths=args.paths,
        )
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(bundle, indent=2))
    else:
        print(format_bundle_markdown(bundle), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
