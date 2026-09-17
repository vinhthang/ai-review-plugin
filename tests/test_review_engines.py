import os
import sys
import tempfile
import json
import signal
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
import peer_review
from review.engines import resolve_engine, WorkBuddyAdapter, CodexAdapter
from review.audit import build_adr_context, _main, main
from review.models import WORKBUDDY_MODEL_MAP

def test_resolve_engine_default_is_workbuddy(monkeypatch):
    monkeypatch.delenv("AI_REVIEW_ENGINE", raising=False)
    engine = peer_review.resolve_engine(cli_engine=None, cli_session_id=None)
    assert engine == "workbuddy", "Default engine must be workbuddy"

def test_resolve_engine_cli_override(monkeypatch):
    monkeypatch.delenv("AI_REVIEW_ENGINE", raising=False)
    assert peer_review.resolve_engine("codex", None) == "codex"
    assert peer_review.resolve_engine("workbuddy", None) == "workbuddy"

def test_resolve_engine_env_override(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_ENGINE", "codex")
    assert peer_review.resolve_engine(None, None) == "codex"
    monkeypatch.setenv("AI_REVIEW_ENGINE", "workbuddy")
    assert peer_review.resolve_engine(None, None) == "workbuddy"

def test_resolve_engine_session_prefix():
    assert peer_review.resolve_engine(None, "workbuddy:uuid-123") == "workbuddy"
    assert peer_review.resolve_engine(None, "codex:uuid-456") == "codex"

def test_resolve_engine_legacy_unprefixed_session_defaults_to_codex(monkeypatch):
    monkeypatch.setenv("AI_REVIEW_ENGINE", "workbuddy")
    # Unprefixed legacy session must route to codex for backward compatibility
    assert peer_review.resolve_engine(None, "legacy-uuid-789") == "codex"

def test_resolve_engine_session_prefix_mismatch_fails():
    with pytest.raises(SystemExit) as exc:
        peer_review.resolve_engine("codex", "workbuddy:uuid-123")
    assert exc.value.code == 2

def test_workbuddy_model_normalization():
    adapter = peer_review.WorkBuddyAdapter()
    assert adapter.normalize_model("deepseek 4.1 flash") == "deepseek-v4.1-flash"
    assert adapter.normalize_model("deepseek-4.1-flash") == "deepseek-v4.1-flash"
    assert adapter.normalize_model("deepseek v4.1 flash") == "deepseek-v4.1-flash"
    assert adapter.normalize_model("deepseek-v4.1-flash") == "deepseek-v4.1-flash"
    assert adapter.normalize_model("deepseek") == "deepseek-v4.1-flash"
    assert adapter.normalize_model("flash") == "deepseek-v4.1-flash"
    assert adapter.normalize_model("fast") == "deepseek-v4.1-flash"
    assert adapter.normalize_model("fast-model") == "deepseek-v4.1-flash"
    assert adapter.normalize_model("balanced") == "balanced-model"
    assert adapter.normalize_model("primary") == "primary-model"
    assert adapter.normalize_model("deep") == "deep-model"
    # Unknown models pass through intact
    assert adapter.normalize_model("custom-model-id") == "custom-model-id"

def test_workbuddy_build_command_flags():
    adapter = peer_review.WorkBuddyAdapter()
    cmd = adapter.build_command(
        launcher_cmd=["node", "/path/to/codebuddy"],
        repo_path="/tmp/repo",
        schema_path="/tmp/schema.json",
        review_file_path="/tmp/review.json",
        prompt_text="Review this file",
        session_id=None,
        model="deepseek 4.1 flash"
    )
    assert cmd[0] == "node"
    assert cmd[1] == "/path/to/codebuddy"
    assert "-p" in cmd
    assert "--model" in cmd
    idx = cmd.index("--model")
    assert cmd[idx + 1] == "deepseek-v4.1-flash"
    assert "--output-format" in cmd
    assert cmd[cmd.index("--output-format") + 1] == "json"
    assert "-y" in cmd
    assert "--tools" not in cmd
    assert "--disallowedTools" in cmd
    assert cmd[cmd.index("--disallowedTools") + 1] == "Bash,Write,Edit,NotebookEdit"
    assert "--json-schema" in cmd
    assert cmd[cmd.index("--json-schema") + 1] == "/tmp/schema.json"
    assert cmd[-1] == "Review this file"

def test_workbuddy_build_command_with_resume():
    adapter = peer_review.WorkBuddyAdapter()
    cmd = adapter.build_command(
        launcher_cmd=["/usr/local/bin/codebuddy"],
        repo_path="/tmp/repo",
        schema_path="/tmp/schema.json",
        review_file_path="/tmp/review.json",
        prompt_text="Resume review",
        session_id="workbuddy:session-uuid-1234",
        model=None
    )
    assert "-r" in cmd
    assert cmd[cmd.index("-r") + 1] == "session-uuid-1234"

def test_workbuddy_stream_parser_json_array(tmp_path):
    adapter = peer_review.WorkBuddyAdapter()
    stdout_file = tmp_path / "stdout.log"
    stderr_file = tmp_path / "stderr.log"
    review_file = tmp_path / "review.json"
    stderr_file.write_text("")

    array_payload = [
        {"type": "init", "message": "starting"},
        {
            "type": "result",
            "subtype": "success",
            "result": json.dumps({"issues": []}),
            "session_id": "test-wb-session-1"
        }
    ]
    stdout_file.write_text(json.dumps(array_payload))

    review, session_id = adapter.extract_review_payload_and_session(
        str(stdout_file), str(stderr_file), str(review_file), None
    )
    assert review == {"issues": []}
    assert session_id == "workbuddy:test-wb-session-1"
    assert review_file.exists()

def test_workbuddy_stream_parser_ndjson(tmp_path):
    adapter = peer_review.WorkBuddyAdapter()
    stdout_file = tmp_path / "stdout.log"
    stderr_file = tmp_path / "stderr.log"
    review_file = tmp_path / "review.json"
    stderr_file.write_text("")

    ndjson_content = (
        '{"type": "message", "content": "thinking"}\n'
        '{"type": "result", "subtype": "success", "result": {"issues": [{"severity": "P2", "description": "minor style"}]}, "session_id": "ndjson-session-2"}\n'
    )
    stdout_file.write_text(ndjson_content)

    review, session_id = adapter.extract_review_payload_and_session(
        str(stdout_file), str(stderr_file), str(review_file), None
    )
    assert len(review["issues"]) == 1
    assert session_id == "workbuddy:ndjson-session-2"

def test_workbuddy_stream_parser_multiple_results_rejected(tmp_path):
    adapter = peer_review.WorkBuddyAdapter()
    stdout_file = tmp_path / "stdout.log"
    stderr_file = tmp_path / "stderr.log"
    review_file = tmp_path / "review.json"
    stderr_file.write_text("")

    multiple_results = [
        {"type": "result", "subtype": "success", "result": "{}", "session_id": "s1"},
        {"type": "result", "subtype": "success", "result": "{}", "session_id": "s2"}
    ]
    stdout_file.write_text(json.dumps(multiple_results))

    with pytest.raises(SystemExit) as exc:
        adapter.extract_review_payload_and_session(str(stdout_file), str(stderr_file), str(review_file), None)
    assert exc.value.code == 2

def test_workbuddy_stream_parser_error_subtype(tmp_path):
    adapter = peer_review.WorkBuddyAdapter()
    stdout_file = tmp_path / "stdout.log"
    stderr_file = tmp_path / "stderr.log"
    review_file = tmp_path / "review.json"
    stderr_file.write_text("")

    error_payload = {
        "type": "result",
        "subtype": "error",
        "error": "Authentication expired"
    }
    stdout_file.write_text(json.dumps(error_payload))

    with pytest.raises(SystemExit) as exc:
        adapter.extract_review_payload_and_session(str(stdout_file), str(stderr_file), str(review_file), None)
    assert exc.value.code == 2

@patch("peer_review.subprocess.Popen")
def test_workbuddy_full_execution_pass(mock_popen, target_and_repo, capsys):
    target, repo = target_and_repo

    def side_effect(cmd, **kwargs):
        if "node" not in cmd[0] and "codebuddy" not in cmd[0]:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.poll.return_value = 0
            mock_proc.wait.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.__enter__.return_value = mock_proc
            return mock_proc

        assert "-p" in cmd
        assert "--model" in cmd
        assert "--output-format" in cmd
        schema_idx = cmd.index("--json-schema")
        schema_path = cmd[schema_idx + 1]
        work_dir = os.path.dirname(schema_path)
        with open(os.path.join(work_dir, "stdout.log"), "w", encoding="utf-8") as f:
            json.dump({
                "type": "result",
                "subtype": "success",
                "result": json.dumps({"issues": []}),
                "session_id": "wb-test-turn-1"
            }, f)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = (b"", b"")
        return mock_proc

    mock_popen.side_effect = side_effect

    with patch("peer_review.WorkBuddyAdapter.resolve_binary", return_value=["node", "/mock/codebuddy"]):
        with patch("sys.argv", ["peer_review.py", "--engine", "workbuddy", "--target", target, "--mode", "design", "--repo", repo, "--no-spec", "--model", "deepseek 4.1 flash"]):
            with pytest.raises(SystemExit) as exc:
                peer_review.main()
            assert exc.value.code == 0

    out, _ = capsys.readouterr()
    envelope = json.loads(out.strip())
    assert envelope["engine"] == "workbuddy"
    assert envelope["session_id"] == "workbuddy:wb-test-turn-1"
    assert envelope["issues"] == []

@patch("peer_review.subprocess.Popen")
def test_workbuddy_full_execution_rejection(mock_popen, target_and_repo, capsys):
    target, repo = target_and_repo

    def side_effect(cmd, **kwargs):
        if "node" not in cmd[0] and "codebuddy" not in cmd[0]:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.poll.return_value = 0
            mock_proc.wait.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.__enter__.return_value = mock_proc
            return mock_proc

        schema_idx = cmd.index("--json-schema")
        schema_path = cmd[schema_idx + 1]
        work_dir = os.path.dirname(schema_path)
        with open(os.path.join(work_dir, "stdout.log"), "w", encoding="utf-8") as f:
            json.dump({
                "type": "result",
                "subtype": "success",
                "result": json.dumps({"issues": [{"severity": "P1", "description": "Critical flaw"}]}),
                "session_id": "wb-test-turn-2"
            }, f)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = (b"", b"")
        return mock_proc

    mock_popen.side_effect = side_effect

    with patch("peer_review.WorkBuddyAdapter.resolve_binary", return_value=["node", "/mock/codebuddy"]):
        with patch("sys.argv", ["peer_review.py", "--engine", "workbuddy", "--target", target, "--mode", "design", "--repo", repo, "--no-spec"]):
            with pytest.raises(SystemExit) as exc:
                peer_review.main()
            assert exc.value.code == 1

    out, _ = capsys.readouterr()
    envelope = json.loads(out.strip())
    assert envelope["engine"] == "workbuddy"
    assert len(envelope["issues"]) == 1
    assert envelope["issues"][0]["severity"] == "P1"

@patch("peer_review.subprocess.Popen")
def test_workbuddy_full_execution_with_extra_properties(mock_popen, target_and_repo, capsys):
    target, repo = target_and_repo

    def side_effect(cmd, **kwargs):
        if "node" not in cmd[0] and "codebuddy" not in cmd[0]:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.poll.return_value = 0
            mock_proc.wait.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.__enter__.return_value = mock_proc
            return mock_proc

        schema_idx = cmd.index("--json-schema")
        schema_path = cmd[schema_idx + 1]
        work_dir = os.path.dirname(schema_path)
        with open(os.path.join(work_dir, "stdout.log"), "w", encoding="utf-8") as f:
            json.dump({
                "type": "result",
                "subtype": "success",
                "result": json.dumps({
                    "issues": [
                        {
                            "severity": "P1",
                            "description": "Critical security bug",
                            "file": "server.py",
                            "line": 42,
                            "title": "Bug Title"
                        }
                    ]
                }),
                "session_id": "wb-test-turn-3"
            }, f)
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_proc.communicate.return_value = (b"", b"")
        return mock_proc

    mock_popen.side_effect = side_effect

    with patch("peer_review.WorkBuddyAdapter.resolve_binary", return_value=["node", "/mock/codebuddy"]):
        with patch("sys.argv", ["peer_review.py", "--engine", "workbuddy", "--target", target, "--mode", "design", "--repo", repo, "--no-spec"]):
            with pytest.raises(SystemExit) as exc:
                peer_review.main()
            assert exc.value.code == 1

    out, _ = capsys.readouterr()
    envelope = json.loads(out.strip())
    assert envelope["engine"] == "workbuddy"
    assert len(envelope["issues"]) == 1
    issue = envelope["issues"][0]
    assert issue["severity"] == "P1"
    assert "file: server.py" in issue["description"]
    assert "line: 42" in issue["description"]
    assert "Critical security bug" in issue["description"]
    assert set(issue.keys()) == {"severity", "description"}


