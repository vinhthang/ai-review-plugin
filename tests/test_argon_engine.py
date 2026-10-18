"""Comprehensive test suite for Argon Web Reviewer & Pluggable Engine Architecture."""
import os
import sys
import json
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))
import peer_review
from review.engines import (
    ReviewEngineAdapter,
    WorkBuddyAdapter,
    CodexAdapter,
    ArgonWebAdapter,
    ENGINE_REGISTRY,
    register_engine,
    get_engine_adapter,
    get_supported_engines,
    resolve_engine,
)
from review.runners import edge_applescript_runner


# ============================================================================
# 1. Pluggable Registry Tests (REQ-036)
# ============================================================================

def test_engine_registry_contains_default_engines():
    engines = get_supported_engines()
    assert "argon-web" in engines
    assert "codex" in engines
    assert "workbuddy" in engines


def test_get_engine_adapter_instances():
    wb = get_engine_adapter("workbuddy")
    assert isinstance(wb, WorkBuddyAdapter)
    cdx = get_engine_adapter("codex")
    assert isinstance(cdx, CodexAdapter)
    argon = get_engine_adapter("argon-web")
    assert isinstance(argon, ArgonWebAdapter)


def test_get_engine_adapter_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported review engine: nonexistent"):
        get_engine_adapter("nonexistent")


def test_register_custom_engine():
    class DummyAdapter(ReviewEngineAdapter):
        def resolve_binary(self): return ["dummy"]
        def build_command(self, *args, **kwargs): return ["dummy"]
        def get_execution_environment(self): return {}
        def extract_review_payload_and_session(self, *args, **kwargs): return {}, "dummy:1"

    register_engine("custom-engine", DummyAdapter)
    assert "custom-engine" in get_supported_engines()
    adapter = get_engine_adapter("custom-engine")
    assert isinstance(adapter, DummyAdapter)
    # Cleanup
    ENGINE_REGISTRY.pop("custom-engine", None)


def test_resolve_engine_argon_web_cli(monkeypatch):
    monkeypatch.delenv("AI_REVIEW_ENGINE", raising=False)
    assert resolve_engine("argon-web", None) == "argon-web"


def test_resolve_engine_argon_web_session(monkeypatch):
    monkeypatch.delenv("AI_REVIEW_ENGINE", raising=False)
    assert resolve_engine(None, "argon-web:sess-123") == "argon-web"


def test_resolve_engine_argon_web_session_mismatch():
    with pytest.raises(SystemExit) as exc:
        resolve_engine("codex", "argon-web:sess-123")
    assert exc.value.code == 2


def test_resolve_engine_env_argon_web(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_ENGINE", "argon-web")
    assert resolve_engine(None, None) == "argon-web"


def test_resolve_engine_unsupported_cli():
    with pytest.raises(SystemExit) as exc:
        resolve_engine("unsupported-xyz", None)
    assert exc.value.code == 2


def test_resolve_engine_unsupported_env(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_ENGINE", "unsupported-xyz")
    with pytest.raises(SystemExit) as exc:
        resolve_engine(None, None)
    assert exc.value.code == 2


# ============================================================================
# 2. ArgonWebAdapter Unit Tests (REQ-038)
# ============================================================================

def test_argon_resolve_binary_success(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/osascript" if cmd == "osascript" else None)
    adapter = ArgonWebAdapter()
    bin_cmd = adapter.resolve_binary()
    assert bin_cmd[0] == sys.executable
    assert bin_cmd[1].endswith("edge_applescript_runner.py")
    assert os.path.isfile(bin_cmd[1])


def test_argon_resolve_binary_missing_osascript(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: None)
    adapter = ArgonWebAdapter()
    with pytest.raises(SystemExit) as exc:
        adapter.resolve_binary()
    assert exc.value.code == 2


def test_argon_resolve_binary_env_override(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/osascript")
    fake_runner = tmp_path / "custom_runner.py"
    fake_runner.write_text("#!/usr/bin/env python3\n")
    monkeypatch.setenv("ARGON_RUNNER_BIN", str(fake_runner))

    adapter = ArgonWebAdapter()
    bin_cmd = adapter.resolve_binary()
    assert bin_cmd == [sys.executable, str(fake_runner)]


def test_argon_resolve_binary_invalid_env_override(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/osascript")
    monkeypatch.setenv("ARGON_RUNNER_BIN", "/nonexistent/runner/path.py")

    adapter = ArgonWebAdapter()
    with pytest.raises(SystemExit) as exc:
        adapter.resolve_binary()
    assert exc.value.code == 2


def test_argon_build_command_default_skill(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    target_file = tmp_path / "target.file"
    target_file.write_text("# Target")

    cmd = adapter.build_command(
        launcher_cmd=[sys.executable, "/path/to/runner.py"],
        repo_path=str(tmp_path),
        schema_path=str(tmp_path / "schema.json"),
        review_file_path=str(review_file),
        prompt_text="Review this doc",
        session_id=None,
        model=None
    )

    assert cmd[0] == sys.executable
    assert cmd[1] == "/path/to/runner.py"
    assert str(target_file) in cmd
    assert "--out" in cmd
    assert cmd[cmd.index("--out") + 1] == str(review_file)
    assert "--schema" in cmd
    assert cmd[cmd.index("--schema") + 1] == str(tmp_path / "schema.json")
    assert "--skill" in cmd
    assert cmd[cmd.index("--skill") + 1] == "@software-architect-reviewer"
    assert "--json-prompt" in cmd
    assert "--prompt" in cmd
    assert cmd[cmd.index("--prompt") + 1] == "Review this doc"


def test_argon_build_command_custom_model_and_env(monkeypatch, tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"

    # 1. Custom model arg overrides env
    monkeypatch.setenv("ARGON_SKILL", "@env-skill")
    cmd = adapter.build_command(
        launcher_cmd=[sys.executable, "/path/to/runner.py"],
        repo_path=str(tmp_path),
        schema_path="",
        review_file_path=str(review_file),
        prompt_text="",
        session_id="argon-web:prior-1",
        model="custom-gem"
    )
    assert cmd[cmd.index("--skill") + 1] == "@custom-gem"

    # 2. Env fallback when model is None
    cmd_env = adapter.build_command(
        launcher_cmd=[sys.executable, "/path/to/runner.py"],
        repo_path=str(tmp_path),
        schema_path="",
        review_file_path=str(review_file),
        prompt_text="",
        session_id=None,
        model=None
    )
    assert cmd_env[cmd_env.index("--skill") + 1] == "@env-skill"


def test_argon_execution_environment():
    adapter = ArgonWebAdapter()
    env = adapter.get_execution_environment()
    assert "PATH" in env
    assert "HOME" in env
    assert "TMPDIR" in env


# ============================================================================
# 3. Hybrid Payload Extraction Tests (REQ-039)
# ============================================================================

def test_extract_missing_review_file(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "missing_review.json"
    with pytest.raises(SystemExit) as exc:
        adapter.extract_review_payload_and_session(
            stdout_path="",
            stderr_path="",
            review_file_path=str(review_file),
            prior_session_id=None
        )
    assert exc.value.code == 2


def test_extract_empty_review_file(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "empty_review.json"
    review_file.write_text("   \n")
    with pytest.raises(SystemExit) as exc:
        adapter.extract_review_payload_and_session(
            stdout_path="",
            stderr_path="",
            review_file_path=str(review_file),
            prior_session_id=None
        )
    assert exc.value.code == 2


def test_extract_direct_json_payload(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    payload = {
        "issues": [
            {"severity": "P0", "description": "Critical flaw in boundary"}
        ]
    }
    review_file.write_text(json.dumps(payload))

    review, session_id = adapter.extract_review_payload_and_session(
        stdout_path="",
        stderr_path="",
        review_file_path=str(review_file),
        prior_session_id=None
    )
    assert len(review["issues"]) == 1
    assert review["issues"][0]["severity"] == "P0"
    assert "Critical flaw" in review["issues"][0]["description"]
    assert session_id.startswith("argon-web:")


def test_extract_direct_json_array_payload(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    payload = [
        {"severity": "P1", "description": "High risk concurrency race"}
    ]
    review_file.write_text(json.dumps(payload))

    review, session_id = adapter.extract_review_payload_and_session(
        stdout_path="",
        stderr_path="",
        review_file_path=str(review_file),
        prior_session_id="argon-web:existing-session-42"
    )
    assert len(review["issues"]) == 1
    assert review["issues"][0]["severity"] == "P1"
    assert session_id == "argon-web:existing-session-42"


def test_extract_fenced_json_payload(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    content = """
    Here is my review based on the software architecture gem:

    ```json
    {
      "issues": [
        {
          "severity": "P2",
          "description": "Consider adding docstrings to public helpers"
        }
      ]
    }
    ```

    Overall the design is in good shape.
    """
    review_file.write_text(content)

    review, session_id = adapter.extract_review_payload_and_session(
        stdout_path="",
        stderr_path="",
        review_file_path=str(review_file),
        prior_session_id="unprefixed-session"
    )
    assert len(review["issues"]) == 1
    assert review["issues"][0]["severity"] == "P2"
    assert session_id == "argon-web:unprefixed-session"


def test_extract_fallback_markdown_severity_tags(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    content = """
    # Peer Review Findings

    * [Critical/Blocker] SQL injection in authentication query.
    - [Critical] Secret key leaked in logging statement.
    1. [Blocker] Deadlock condition during concurrent cache invalidation.
    * [Warning] Unbounded memory growth in audit log queue.
    ### [Suggestion] Add type hints to edge_applescript_runner.py.
    """
    review_file.write_text(content)

    review, _ = adapter.extract_review_payload_and_session(
        stdout_path="",
        stderr_path="",
        review_file_path=str(review_file),
        prior_session_id=None
    )
    issues = review["issues"]
    assert len(issues) == 5

    # Check P0 mappings
    p0_issues = [i for i in issues if i["severity"] == "P0"]
    assert len(p0_issues) == 3
    assert any("SQL injection" in i["description"] for i in p0_issues)
    assert any("Secret key leaked" in i["description"] for i in p0_issues)
    assert any("Deadlock condition" in i["description"] for i in p0_issues)

    # Check P1 mappings
    p1_issues = [i for i in issues if i["severity"] == "P1"]
    assert len(p1_issues) == 1
    assert "Unbounded memory growth" in p1_issues[0]["description"]

    # Check P2 mappings
    p2_issues = [i for i in issues if i["severity"] == "P2"]
    assert len(p2_issues) == 1
    assert "Add type hints" in p2_issues[0]["description"]


def test_extract_explicit_clean_approval_markdown(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    review_file.write_text("I have examined all components. No issues found. The architecture is clean.")

    review, _ = adapter.extract_review_payload_and_session(
        stdout_path="",
        stderr_path="",
        review_file_path=str(review_file),
        prior_session_id=None
    )
    assert review == {"issues": []}


def test_extract_unparseable_malformed_payload(tmp_path):
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    review_file.write_text("502 Server Error: Gateway timeout occurred while upstream processing.")

    with pytest.raises(SystemExit) as exc:
        adapter.extract_review_payload_and_session(
            stdout_path="",
            stderr_path="",
            review_file_path=str(review_file),
            prior_session_id=None
        )
    assert exc.value.code == 2


# ============================================================================
# 4. edge_applescript_runner Unit Tests (REQ-037)
# ============================================================================

def test_bundle_markdown_files_with_files(tmp_path):
    f1 = tmp_path / "doc1.md"
    f1.write_text("Content 1")
    f2 = tmp_path / "doc2.md"
    f2.write_text("Content 2")

    bundle = edge_applescript_runner.bundle_markdown_files(
        [str(f1), str(f2)],
        skill_name="software-architect-reviewer",
        json_prompt=True,
        prompt_text="Extra prompt context"
    )

    assert "@software-architect-reviewer" in bundle
    assert "Extra prompt context" in bundle
    assert "doc1.md" in bundle
    assert "Content 1" in bundle
    assert "doc2.md" in bundle
    assert "Content 2" in bundle
    assert '"issues": [' in bundle


def test_bundle_markdown_files_default_markdown_instructions(tmp_path):
    f1 = tmp_path / "doc.md"
    f1.write_text("Spec content")

    bundle = edge_applescript_runner.bundle_markdown_files(
        [str(f1)],
        json_prompt=False
    )
    assert "[Critical/Blocker]" in bundle
    assert "[Warning]" in bundle
    assert "[Suggestion]" in bundle


def test_run_edge_js_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="https://gemini.google.com/app\n", stderr="")
        res = edge_applescript_runner.run_edge_js("window.location.href")
        assert res == "https://gemini.google.com/app"


def test_run_edge_js_no_tab_found():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="NO_GEMINI_TAB_FOUND\n", stderr="")
        with pytest.raises(RuntimeError, match="No open tab with gemini.google.com found"):
            edge_applescript_runner.run_edge_js("window.location.href")


def test_run_edge_js_applescript_permission_error():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="execution error: Allow JavaScript from Apple Events is not enabled (-1708)"
        )
        with pytest.raises(RuntimeError, match="AppleScript error:"):
            edge_applescript_runner.run_edge_js("window.location.href")


def test_edge_runner_main_mocked_success(tmp_path):
    doc = tmp_path / "test_doc.md"
    doc.write_text("# Design document")
    out_file = tmp_path / "review_out.md"

    # Simulate sequence of JS calls:
    # 1. URL check -> "https://gemini.google.com/app"
    # 2. Inject prompt -> "OK"
    # 3. Dismiss popover -> "OK"
    # 4. Initial count check -> "0"
    # 5. Click send -> "CLICKED: send"
    # 6. Stream status 1 (pre-wait, count 1 > 0) -> done, length 200
    # 7. Stream status 2 (stability check 1) -> done, length 200
    # 8. Stream status 3 (stability check 2) -> done, length 200 (stable)
    # 9. Extract response -> "```json\n{\"issues\": []}\n```"
    js_responses = [
        "https://gemini.google.com/app",
        "OK",
        "OK",
        "0",
        "CLICKED: send",
        json.dumps({"isStreaming": False, "count": 1, "textLen": 200}),
        json.dumps({"isStreaming": False, "count": 1, "textLen": 200}),
        json.dumps({"isStreaming": False, "count": 1, "textLen": 200}),
        json.dumps({"isStreaming": False, "count": 1, "textLen": 200}),
        "```json\n{\"issues\": []}\n```"
    ]

    with patch("review.runners.edge_applescript_runner.run_edge_js", side_effect=js_responses):
        with patch("time.sleep", return_value=None):
            edge_applescript_runner.main([
                str(doc),
                "--out", str(out_file),
                "--json-prompt",
                "--timeout", "10"
            ])

    assert out_file.exists()
    assert '{"issues": []}' in out_file.read_text(encoding="utf-8")


def test_edge_runner_main_injection_failure(tmp_path):
    doc = tmp_path / "test_doc.md"
    doc.write_text("# Design document")

    with patch("review.runners.edge_applescript_runner.run_edge_js", side_effect=["https://gemini.google.com/app", "INPUT_NOT_FOUND"]):
        with patch("time.sleep", return_value=None):
            with pytest.raises(SystemExit) as exc:
                edge_applescript_runner.main([str(doc)])
            assert exc.value.code == 1


# ============================================================================
# 5. Full Pipeline End-to-End Mock Execution (REQ-040)
# ============================================================================

@patch("peer_review.subprocess.Popen")
def test_argon_full_execution_pass(mock_popen, target_and_repo, capsys):
    target, repo = target_and_repo

    def side_effect(cmd, **kwargs):
        # Allow rsync or other utility commands to proceed cleanly
        if "edge_applescript_runner.py" not in cmd[1] and "runner.py" not in cmd[1]:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.poll.return_value = 0
            mock_proc.wait.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.__enter__.return_value = mock_proc
            return mock_proc

        assert "--json-prompt" in cmd
        assert "--out" in cmd
        out_idx = cmd.index("--out")
        review_file = cmd[out_idx + 1]

        # Simulate runner writing clean review JSON
        with open(review_file, "w", encoding="utf-8") as f:
            f.write("```json\n{\"issues\": []}\n```")

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = (b"", b"")
        return mock_proc

    mock_popen.side_effect = side_effect

    with patch("peer_review.ArgonWebAdapter.resolve_binary", return_value=[sys.executable, "/mock/edge_applescript_runner.py"]):
        with patch("sys.argv", [
            "peer_review.py",
            "--engine", "argon-web",
            "--target", target,
            "--mode", "design",
            "--repo", repo,
            "--no-spec"
        ]):
            with pytest.raises(SystemExit) as exc:
                peer_review.main()
            assert exc.value.code == 0

    out, _ = capsys.readouterr()
    envelope = json.loads(out.strip())
    assert envelope["engine"] == "argon-web"
    assert envelope["session_id"].startswith("argon-web:")
    assert envelope["issues"] == []


@patch("peer_review.subprocess.Popen")
def test_argon_full_execution_rejection(mock_popen, target_and_repo, capsys):
    target, repo = target_and_repo

    def side_effect(cmd, **kwargs):
        if "edge_applescript_runner.py" not in cmd[1] and "runner.py" not in cmd[1]:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.poll.return_value = 0
            mock_proc.wait.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.__enter__.return_value = mock_proc
            return mock_proc

        out_idx = cmd.index("--out")
        review_file = cmd[out_idx + 1]

        # Simulate runner writing review with a blocker
        with open(review_file, "w", encoding="utf-8") as f:
            f.write("""
            Review findings:
            * [Critical/Blocker] Unauthorized API access allowed in auth endpoint.
            """)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = (b"", b"")
        return mock_proc

    mock_popen.side_effect = side_effect

    with patch("peer_review.ArgonWebAdapter.resolve_binary", return_value=[sys.executable, "/mock/edge_applescript_runner.py"]):
        with patch("sys.argv", [
            "peer_review.py",
            "--engine", "argon-web",
            "--target", target,
            "--mode", "design",
            "--repo", repo,
            "--no-spec"
        ]):
            with pytest.raises(SystemExit) as exc:
                peer_review.main()
            assert exc.value.code == 1

    out, _ = capsys.readouterr()
    envelope = json.loads(out.strip())
    assert envelope["engine"] == "argon-web"
    assert len(envelope["issues"]) == 1
    assert envelope["issues"][0]["severity"] == "P0"
    assert "Unauthorized API access" in envelope["issues"][0]["description"]


# ============================================================================
# 6. Hardening & Verification Unit Tests (REQ-041)
# ============================================================================

def test_extract_reverse_code_fence_search(tmp_path):
    """Test reverse search ignores earlier illustrative code blocks inside design docs."""
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    content = """
    # Architectural Design Document

    Here is an illustrative schema and example snippet inside the design doc:
    ```json
    {
      "database": "postgres",
      "port": 5432
    }
    ```

    Another example payload from the design doc:
    ```json
    {
      "issues": "this is not a list, illustrative text"
    }
    ```

    Yet another example snippet:
    ```json
    {
      "issues": [
        {"severity": "P2", "description": "Example doc issue that should be ignored"}
      ]
    }
    ```

    # Reviewer Response
    ```json
    {
      "issues": [
        {
          "severity": "P0",
          "description": "Actual reviewer critical finding: authentication bypass"
        }
      ]
    }
    ```
    """
    review_file.write_text(content)
    review, _ = adapter.extract_review_payload_and_session(
        stdout_path="",
        stderr_path="",
        review_file_path=str(review_file),
        prior_session_id=None
    )
    assert len(review["issues"]) == 1
    assert review["issues"][0]["severity"] == "P0"
    assert "Actual reviewer critical finding: authentication bypass" in review["issues"][0]["description"]


@pytest.mark.parametrize("banner", [
    "I am sorry, something went wrong while processing your request.",
    "Error: usage limit reached for today.",
    "Safety refusal: I cannot fulfill this review request.",
    "We are unable to process this document due to size constraints.",
    "Error: internal server exception.",
])
def test_extract_fail_closed_on_error_banners(tmp_path, banner):
    """Test fail-closed behavior on model error/refusal banners."""
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    review_file.write_text(banner)

    with pytest.raises(SystemExit) as exc:
        adapter.extract_review_payload_and_session(
            stdout_path="",
            stderr_path="",
            review_file_path=str(review_file),
            prior_session_id=None
        )
    assert exc.value.code == 2


def test_extract_fail_closed_error_banner_with_positive_sentinel(tmp_path):
    """Test error banner forces fail-closed even if positive sentinels appear in output."""
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    review_file.write_text("something went wrong! Status: approved. All checks passed.")

    with pytest.raises(SystemExit) as exc:
        adapter.extract_review_payload_and_session(
            stdout_path="",
            stderr_path="",
            review_file_path=str(review_file),
            prior_session_id=None
        )
    assert exc.value.code == 2


def test_extract_explicit_approval_sentinels(tmp_path):
    """Test positive review approval sentinels yield zero issues."""
    adapter = ArgonWebAdapter()
    for idx, sentinel in enumerate([
        "Status: approved. Ready to deploy.",
        "Verdict: approved. Clean architecture.",
        "Review passed. No defects found.",
        "All checks passed successfully."
    ]):
        review_file = tmp_path / f"review_{idx}.json"
        review_file.write_text(sentinel)
        review, _ = adapter.extract_review_payload_and_session(
            stdout_path="",
            stderr_path="",
            review_file_path=str(review_file),
            prior_session_id=None
        )
        assert review == {"issues": []}


def test_strict_bijective_severity_mappings_bracketed_json(tmp_path):
    """Test bracketed severity tags in JSON map bijectively to P0, P1, P2."""
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    payload = {
        "issues": [
            {"severity": "[Critical/Blocker]", "description": "Defect 1"},
            {"severity": "[Critical]", "description": "Defect 2"},
            {"severity": "[Blocker]", "description": "Defect 3"},
            {"severity": "[Warning]", "description": "Defect 4"},
            {"severity": "[Suggestion]", "description": "Defect 5"},
        ]
    }
    review_file.write_text(json.dumps(payload))
    review, _ = adapter.extract_review_payload_and_session(
        stdout_path="",
        stderr_path="",
        review_file_path=str(review_file),
        prior_session_id=None
    )
    assert [i["severity"] for i in review["issues"]] == ["P0", "P0", "P0", "P1", "P2"]


def test_strict_bijective_severity_mappings_markdown_tags(tmp_path):
    """Test bracketed severity tags in markdown fallback map bijectively to P0, P1, P2."""
    adapter = ArgonWebAdapter()
    review_file = tmp_path / "review.json"
    content = """
    # Security and Architecture Review

    * [Critical/Blocker] SQL injection in search endpoint.
    * [Critical] Hardcoded credentials in repo.
    * [Blocker] Thread deadlock in connection pool.
    * [Warning] Missing rate limiting on public route.
    * [Suggestion] Consider using dataclasses instead of dicts.
    """
    review_file.write_text(content)
    review, _ = adapter.extract_review_payload_and_session(
        stdout_path="",
        stderr_path="",
        review_file_path=str(review_file),
        prior_session_id=None
    )
    assert [i["severity"] for i in review["issues"]] == ["P0", "P0", "P0", "P1", "P2"]


def test_edge_runner_stale_dom_count_prevention(tmp_path):
    """Test Edge runner waits until count > initial_count before completion stability polling."""
    doc = tmp_path / "test_doc.md"
    doc.write_text("# Design document")
    out_file = tmp_path / "review_out.md"

    # Simulate sequence where initial_count is 2:
    # Call 6 is pre-wait check where count is still 2 -> does not exit pre-wait
    # Call 7 is pre-wait check where count is 3 (> 2) -> exits pre-wait
    # Calls 8, 9, 10 are stability checks -> stable
    # Call 11 is extract_js
    js_responses = [
        "https://gemini.google.com/app",
        "OK",
        "OK",
        "2",
        "CLICKED: send",
        json.dumps({"isStreaming": False, "count": 2, "textLen": 100}),
        json.dumps({"isStreaming": False, "count": 3, "textLen": 250}),
        json.dumps({"isStreaming": False, "count": 3, "textLen": 250}),
        json.dumps({"isStreaming": False, "count": 3, "textLen": 250}),
        json.dumps({"isStreaming": False, "count": 3, "textLen": 250}),
        "```json\n{\"issues\": []}\n```"
    ]

    with patch("review.runners.edge_applescript_runner.run_edge_js", side_effect=js_responses):
        with patch("time.sleep", return_value=None):
            edge_applescript_runner.main([
                str(doc),
                "--out", str(out_file),
                "--json-prompt",
                "--timeout", "10"
            ])

    assert out_file.exists()
    assert '{"issues": []}' in out_file.read_text(encoding="utf-8")


def test_engine_session_prefixes_dict():
    """Verify ENGINE_SESSION_PREFIXES dictionary decoupling."""
    from review.engines import ENGINE_SESSION_PREFIXES
    assert ENGINE_SESSION_PREFIXES["workbuddy:"] == "workbuddy"
    assert ENGINE_SESSION_PREFIXES["codex:"] == "codex"
    assert ENGINE_SESSION_PREFIXES["argon-web:"] == "argon-web"

