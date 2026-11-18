#!/usr/bin/env python3
"""Repo convention auto-discovery and fast read-only scoped CLI linters (REQ-052)."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any

CONVENTION_FILES: tuple[str, ...] = (
    "CONTRIBUTING.md",
    "STYLEGUIDE.md",
    ".editorconfig",
    "go.mod",
    ".golangci.yml",
    ".golangci.yaml",
    "staticcheck.conf",
    "checkstyle.xml",
    "config/checkstyle/checkstyle.xml",
    "pmd.xml",
    "spotbugs-exclude.xml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "pyproject.toml",
    ".ruff.toml",
    "ruff.toml",
    ".flake8",
    "setup.cfg",
    "mypy.ini",
    "tsconfig.json",
    "biome.json",
    "biome.jsonc",
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    ".eslintrc.cjs",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
    ".prettierrc",
    ".prettierrc.json",
    "Cargo.toml",
    "rustfmt.toml",
    ".rustfmt.toml",
    "clippy.toml",
    ".swiftlint.yml",
    ".swift-format",
    ".swiftformat",
    "Package.swift",
    "detekt.yml",
    "config/detekt/detekt.yml",
    "lint.xml",
    "gradle/libs.versions.toml",
)

ESLINT_CONFIGS: tuple[str, ...] = (
    ".eslintrc",
    ".eslintrc.json",
    ".eslintrc.js",
    ".eslintrc.cjs",
    "eslint.config.js",
    "eslint.config.mjs",
    "eslint.config.cjs",
)

HUNK_HEADER_RE = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@")
DIAG_LINE_RE = re.compile(r"^(?:\[(?:ERROR|WARN|INFO)\]\s+)?(.+?):(\d+)(?::\d+)?:\s*(.+)$")
GO_VERSION_RE = re.compile(r"^\s*go\s+(\d+\.\d+(?:\.\d+)?)\b", re.MULTILINE)
PYPROJECT_TOOL_RE = re.compile(r"^\[tool\.([A-Za-z0-9_-]+)", re.MULTILINE)


def discover_repo_conventions(repo_root: Path, changed_files: list[str]) -> dict[str, Any]:
    """Detect repository style/linter configurations and language versions."""
    config_files = [rel for rel in CONVENTION_FILES if (repo_root / rel).is_file()]

    go_version: str | None = None
    go_mod = repo_root / "go.mod"
    if go_mod.is_file():
        m = GO_VERSION_RE.search(go_mod.read_text(encoding="utf-8", errors="replace"))
        if m:
            go_version = m.group(1)

    python_tools: list[str] = []
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        for tool in PYPROJECT_TOOL_RE.findall(pyproject.read_text(encoding="utf-8", errors="replace")):
            if tool not in python_tools:
                python_tools.append(tool)
    for cfg_name, tool_name in (
        (".ruff.toml", "ruff"),
        ("ruff.toml", "ruff"),
        (".flake8", "flake8"),
        ("mypy.ini", "mypy"),
    ):
        if (repo_root / cfg_name).is_file() and tool_name not in python_tools:
            python_tools.append(tool_name)

    java_configs: dict[str, str] = {}
    for candidate in ("checkstyle.xml", "config/checkstyle/checkstyle.xml"):
        if (repo_root / candidate).is_file():
            java_configs["checkstyle"] = candidate
            break
    if (repo_root / "pmd.xml").is_file():
        java_configs["pmd"] = "pmd.xml"
    if (repo_root / "spotbugs-exclude.xml").is_file():
        java_configs["spotbugs"] = "spotbugs-exclude.xml"

    kotlin_configs: dict[str, str] = {}
    for detekt_candidate in ("detekt.yml", "config/detekt/detekt.yml"):
        if (repo_root / detekt_candidate).is_file():
            kotlin_configs["detekt"] = detekt_candidate
            break
    if (repo_root / "lint.xml").is_file():
        kotlin_configs["android_lint"] = "lint.xml"

    swift_configs: dict[str, str] = {}
    if (repo_root / ".swiftlint.yml").is_file():
        swift_configs["swiftlint"] = ".swiftlint.yml"
    for sf_candidate in (".swift-format", ".swiftformat"):
        if (repo_root / sf_candidate).is_file():
            swift_configs["swift_format"] = sf_candidate
            break

    deep_lint_hints: list[str] = []
    has_java = any(f.endswith(".java") for f in changed_files)
    has_kotlin = any(f.endswith((".kt", ".kts")) for f in changed_files)
    has_swift = any(f.endswith(".swift") for f in changed_files)
    has_rust = any(f.endswith(".rs") for f in changed_files)
    if (has_java or has_kotlin) and any((repo_root / p).is_file() for p in ("pom.xml", "build.gradle", "build.gradle.kts")):
        deep_lint_hints.append("JVM/Android build config detected; pass --deep-lint to run Maven/Gradle checks")
    if has_swift and (repo_root / "Package.swift").is_file():
        deep_lint_hints.append("Package.swift detected; pass --deep-lint to run swift build --build-tests")
    if has_rust and (repo_root / "Cargo.toml").is_file():
        deep_lint_hints.append("Cargo.toml detected; pass --deep-lint to run cargo clippy")

    return {
        "config_files": config_files,
        "go_version": go_version,
        "python_tools": python_tools,
        "java_configs": java_configs,
        "kotlin_configs": kotlin_configs,
        "swift_configs": swift_configs,
        "deep_lint_hints": deep_lint_hints,
    }


def parse_changed_lines(diff_text: str) -> dict[str, set[int]]:
    """Parse unified diff text into per-file sets of added/modified target line numbers."""
    changed: dict[str, set[int]] = {}
    current_file: str | None = None
    in_hunk = False
    new_line = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            in_hunk = False
            current_file = None
            continue
        if line.startswith("+++ b/"):
            raw = line[6:].split("\t", 1)[0].strip().strip("'\"")
            current_file = raw[2:] if raw.startswith("./") else raw
            in_hunk = False
            continue
        if line.startswith("+++ /dev/null"):
            current_file = None
            in_hunk = False
            continue
        if line.startswith("--- "):
            continue

        hunk_match = HUNK_HEADER_RE.match(line)
        if hunk_match:
            new_line = int(hunk_match.group(1))
            in_hunk = current_file is not None
            continue

        if not in_hunk or current_file is None:
            continue

        if line.startswith("+"):
            changed.setdefault(current_file, set()).add(new_line)
            new_line += 1
        elif line.startswith("-"):
            continue
        elif line.startswith(" "):
            new_line += 1
        elif line.startswith("\\ No newline"):
            continue
        else:
            in_hunk = False

    return changed


def _normalize_diag_path(raw_path: str, repo_root: Path) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
    path_obj = Path(cleaned)
    if path_obj.is_absolute():
        try:
            cleaned = path_obj.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            cleaned = path_obj.as_posix()
    if cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned


def _parse_diagnostic_lines(
    output: str,
    tool: str,
    repo_root: Path,
    changed_lines_by_file: dict[str, set[int]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for raw_line in output.splitlines():
        m = DIAG_LINE_RE.match(raw_line.strip())
        if not m:
            continue
        rel_file = _normalize_diag_path(m.group(1), repo_root)
        line_num = int(m.group(2))
        message = m.group(3).strip()
        in_hunk = line_num in changed_lines_by_file.get(rel_file, set())
        findings.append(
            {
                "tool": tool,
                "file": rel_file,
                "line": line_num,
                "message": message,
                "in_diff_hunk": in_hunk,
            }
        )
    return findings


def _run_tool(
    tool_name: str,
    cmd: list[str],
    repo_root: Path,
    timeout_sec: int,
    run_env: dict[str, str],
    executed: list[str],
    skipped: list[str],
) -> str | None:
    if shutil.which(cmd[0], path=run_env.get("PATH", "")) is None:
        skipped.append(f"{tool_name} (not installed)")
        return None

    proc = subprocess.Popen(
        cmd,
        cwd=repo_root,
        env=run_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError) as kill_err:
            _ = kill_err
        proc.kill()
        proc.communicate()
        skipped.append(f"{tool_name} (timed out after {timeout_sec}s)")
        return None

    executed.append(" ".join(cmd))
    return "\n".join(part for part in (stdout, stderr) if part)


def _run_git_diff_check(
    repo_root: Path,
    existing_files: list[str],
    changed_lines_by_file: dict[str, set[int]],
    timeout_sec: int,
    run_env: dict[str, str],
    findings: list[dict[str, Any]],
    executed: list[str],
    skipped: list[str],
) -> None:
    if shutil.which("git", path=run_env.get("PATH", "")) is None:
        skipped.append("git-diff-check (not installed)")
        return

    head_probe = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=repo_root,
        env=run_env,
        capture_output=True,
        text=True,
    )
    if head_probe.returncode == 0 and existing_files:
        cmd = ["git", "diff", "--check", "HEAD", "--", *existing_files]
    else:
        cmd = ["git", "diff", "--check"]

    output = _run_tool("git-diff-check", cmd, repo_root, timeout_sec, run_env, executed, skipped)
    if output:
        findings.extend(_parse_diagnostic_lines(output, "git-diff-check", repo_root, changed_lines_by_file))


def _unique_go_packages(go_files: list[str]) -> list[str]:
    pkgs: list[str] = []
    for rel in go_files:
        parent = Path(rel).parent.as_posix()
        pkg = "." if parent in ("", ".") else f"./{parent}"
        if pkg not in pkgs:
            pkgs.append(pkg)
    return pkgs


def run_scoped_linters(
    repo_root: Path,
    changed_files: list[str],
    changed_lines_by_file: dict[str, set[int]],
    *,
    deep_lint: bool = False,
    timeout_sec: int = 15,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run read-only scoped linters against changed files/packages without mutating files."""
    run_env = dict(env) if env is not None else os.environ.copy()
    findings: list[dict[str, Any]] = []
    executed: list[str] = []
    skipped: list[str] = []

    existing_files = [rel for rel in changed_files if (repo_root / rel).is_file()]
    _run_git_diff_check(
        repo_root, existing_files, changed_lines_by_file, timeout_sec, run_env, findings, executed, skipped
    )

    py_files = [f for f in existing_files if f.endswith((".py", ".pyi"))]
    go_files = [f for f in existing_files if f.endswith(".go")]
    java_files = [f for f in existing_files if f.endswith(".java")]
    kt_files = [f for f in existing_files if f.endswith((".kt", ".kts"))]
    swift_files = [f for f in existing_files if f.endswith(".swift")]
    rs_files = [f for f in existing_files if f.endswith(".rs")]
    sh_files = [f for f in existing_files if f.endswith((".sh", ".bash"))]
    wf_files = [f for f in existing_files if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))]
    js_files = [f for f in existing_files if f.endswith((".ts", ".tsx", ".js", ".jsx"))]

    tool_jobs: list[tuple[str, list[str], int]] = []
    if py_files:
        tool_jobs.append(("ruff", ["ruff", "check", "--output-format", "concise", "--no-fix", "--", *py_files], timeout_sec))

    if go_files:
        go_pkgs = _unique_go_packages(go_files)
        gofmt_out = _run_tool("gofmt", ["gofmt", "-l", "--", *go_files], repo_root, timeout_sec, run_env, executed, skipped)
        if gofmt_out:
            for line in gofmt_out.splitlines():
                rel = _normalize_diag_path(line, repo_root)
                if rel:
                    findings.append(
                        {
                            "tool": "gofmt",
                            "file": rel,
                            "line": None,
                            "message": "File is not gofmt-formatted",
                            "in_diff_hunk": bool(changed_lines_by_file.get(rel)),
                        }
                    )
        tool_jobs.append(("go-vet", ["go", "vet", *go_pkgs], timeout_sec))
        if shutil.which("golangci-lint", path=run_env.get("PATH", "")) is not None:
            tool_jobs.append(("golangci-lint", ["golangci-lint", "run", "--fast", *go_pkgs], timeout_sec))
        else:
            skipped.append("golangci-lint (not installed)")
            if shutil.which("staticcheck", path=run_env.get("PATH", "")) is not None:
                tool_jobs.append(("staticcheck", ["staticcheck", *go_pkgs], timeout_sec))

    if java_files:
        cfg = "/google_checks.xml"
        for candidate in ("checkstyle.xml", "config/checkstyle/checkstyle.xml"):
            if (repo_root / candidate).is_file():
                cfg = candidate
                break
        tool_jobs.append(("checkstyle", ["checkstyle", "-c", cfg, *java_files], timeout_sec))
        tool_jobs.append(("pmd", ["pmd", "check", "-d", ",".join(java_files), "-R", "rulesets/java/quickstart.xml", "-f", "text"], timeout_sec))

    if kt_files:
        tool_jobs.append(("ktlint", ["ktlint", "--relative", *kt_files], timeout_sec))
        detekt_cmd = ["detekt", "--input", ",".join(kt_files)]
        for detekt_candidate in ("detekt.yml", "config/detekt/detekt.yml"):
            if (repo_root / detekt_candidate).is_file():
                detekt_cmd.extend(["-c", detekt_candidate])
                break
        tool_jobs.append(("detekt", detekt_cmd, timeout_sec))

    if swift_files:
        tool_jobs.append(("swiftlint", ["swiftlint", "lint", "--quiet", "--", *swift_files], timeout_sec))
        tool_jobs.append(("swift-format", ["swift-format", "lint", *swift_files], timeout_sec))

    if rs_files:
        tool_jobs.append(("rustfmt", ["rustfmt", "--check", "--", *rs_files], timeout_sec))
    if sh_files:
        tool_jobs.append(("shellcheck", ["shellcheck", "-f", "gcc", "--", *sh_files], timeout_sec))
    if wf_files:
        tool_jobs.append(("actionlint", ["actionlint", *wf_files], timeout_sec))

    if js_files:
        if (repo_root / "biome.json").is_file() or (repo_root / "biome.jsonc").is_file():
            tool_jobs.append(("biome", ["biome", "check", *js_files], timeout_sec))
        elif any((repo_root / cfg).is_file() for cfg in ESLINT_CONFIGS):
            tool_jobs.append(("eslint", ["eslint", "--no-fix", *js_files], timeout_sec))

    if deep_lint:
        deep_timeout = max(timeout_sec, 60)
        if java_files and (repo_root / "pom.xml").is_file():
            tool_jobs.append(("mvn", ["mvn", "-q", "checkstyle:check", "-DskipTests"], deep_timeout))
        elif (java_files or kt_files) and any((repo_root / g).is_file() for g in ("build.gradle", "build.gradle.kts")):
            tool_jobs.append(("gradle", ["gradle", "check", "-x", "test", "--no-daemon"], deep_timeout))
        if swift_files and (repo_root / "Package.swift").is_file():
            tool_jobs.append(("swift", ["swift", "build", "--build-tests"], deep_timeout))
        if rs_files and (repo_root / "Cargo.toml").is_file():
            tool_jobs.append(("cargo", ["cargo", "clippy", "--no-deps", "--message-format", "short"], deep_timeout))

    for tool_name, cmd, t_sec in tool_jobs:
        output = _run_tool(tool_name, cmd, repo_root, t_sec, run_env, executed, skipped)
        if output:
            findings.extend(_parse_diagnostic_lines(output, tool_name, repo_root, changed_lines_by_file))

    return {
        "findings": findings,
        "executed": executed,
        "skipped": skipped,
    }
