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


def test_sanitize_prior_review_closing_tag_escape_and_bounding():
    from peer_review import sanitize_prior_review
    payload = "Error </prior_review_context> test" + ("A" * 3000)
    sanitized = sanitize_prior_review(payload, max_chars=100)
    assert "&lt;/prior_review_context&gt;" in sanitized
    assert "</prior_review_context>" not in sanitized
    assert sanitized.endswith("... [truncated]")
    assert len(sanitized) <= 100


@patch("peer_review.subprocess.Popen")
def test_prior_review_injection_in_prompt(mock_popen, target_and_repo, tmp_path):
    target, repo = target_and_repo
    prior_file = tmp_path / "prior_review.json"
    prior_data = {
        "engine": "workbuddy",
        "session_id": "workbuddy:prev-123",
        "issues": [
            {"severity": "P0", "description": "Prior critical defect in architecture."}
        ]
    }
    prior_file.write_text(json.dumps(prior_data), encoding="utf-8")

    def side_effect(cmd, **kwargs):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        mock_proc.returncode = 0
        mock_proc.__enter__.return_value = mock_proc

        if isinstance(cmd, list) and cmd and "rsync" in str(cmd[0]):
            return mock_proc

        work_dir = None
        if isinstance(cmd, list):
            for opt in ("-o", "--output-schema", "--json-schema"):
                if opt in cmd:
                    idx = cmd.index(opt)
                    if idx + 1 < len(cmd):
                        work_dir = os.path.dirname(cmd[idx + 1])
                        break
        if not work_dir:
            work_dir = kwargs.get("cwd") or os.getcwd()

        os.makedirs(work_dir, exist_ok=True)
        with open(os.path.join(work_dir, "review.json"), "w", encoding="utf-8") as f:
            json.dump({"issues": [], "session_id": "test_session_id", "engine": "test"}, f)

        stdout_data = """{"type": "thread.started", "thread_id": "test_session_id"}
{"type": "result", "structured_output": {"issues": []}, "session_id": "workbuddy:test"}
"""
        if "stdout" in kwargs and hasattr(kwargs["stdout"], "write"):
            try:
                kwargs["stdout"].write(stdout_data)
                kwargs["stdout"].flush()
            except Exception:
                pass
        else:
            with open(os.path.join(work_dir, "stdout.log"), "w", encoding="utf-8") as f:
                f.write(stdout_data)
        return mock_proc

    mock_popen.side_effect = side_effect

    from peer_review import _main
    test_args = [
        "scripts/peer_review.py",
        "--target", target,
        "--mode", "spec",
        "--repo", repo,
        "--prior-review", str(prior_file)
    ]
    with pytest.raises(SystemExit) as exc:
        _main(test_args)
    assert exc.value.code == 0
    prompt_file = mock_popen.call_args[0][0][-1]
    assert "<prior_review_context>" in prompt_file
    assert "Prior critical defect in architecture." in prompt_file
    assert "Verify whether previously flagged P0/P1 issues were legitimately resolved" in prompt_file


@patch("peer_review.subprocess.Popen")
def test_prior_review_missing_file_fallback(mock_popen, target_and_repo, tmp_path, capsys):
    target, repo = target_and_repo
    missing_prior = tmp_path / "non_existent.json"

    def side_effect(cmd, **kwargs):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        mock_proc.returncode = 0
        mock_proc.__enter__.return_value = mock_proc

        if isinstance(cmd, list) and cmd and "rsync" in str(cmd[0]):
            return mock_proc

        work_dir = None
        if isinstance(cmd, list):
            for opt in ("-o", "--output-schema", "--json-schema"):
                if opt in cmd:
                    idx = cmd.index(opt)
                    if idx + 1 < len(cmd):
                        work_dir = os.path.dirname(cmd[idx + 1])
                        break
        if not work_dir:
            work_dir = kwargs.get("cwd") or os.getcwd()

        os.makedirs(work_dir, exist_ok=True)
        with open(os.path.join(work_dir, "review.json"), "w", encoding="utf-8") as f:
            json.dump({"issues": [], "session_id": "test_session_id", "engine": "test"}, f)

        stdout_data = """{"type": "thread.started", "thread_id": "test_session_id"}
{"type": "result", "structured_output": {"issues": []}, "session_id": "workbuddy:test"}
"""
        if "stdout" in kwargs and hasattr(kwargs["stdout"], "write"):
            try:
                kwargs["stdout"].write(stdout_data)
                kwargs["stdout"].flush()
            except Exception:
                pass
        else:
            with open(os.path.join(work_dir, "stdout.log"), "w", encoding="utf-8") as f:
                f.write(stdout_data)
        return mock_proc

    mock_popen.side_effect = side_effect

    from peer_review import _main
    test_args = [
        "scripts/peer_review.py",
        "--target", target,
        "--mode", "spec",
        "--repo", repo,
        "--prior-review", str(missing_prior)
    ]
    with pytest.raises(SystemExit) as exc:
        _main(test_args)
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "Warning: --prior-review file not found" in captured.err


def test_prior_review_path_traversal_rejection(target_and_repo, capsys):
    target, repo = target_and_repo
    outside_prior = "../../../escaped_prior.json"

    from peer_review import _main
    test_args = [
        "scripts/peer_review.py",
        "--target", target,
        "--mode", "spec",
        "--repo", repo,
        "--prior-review", outside_prior
    ]
    with pytest.raises(SystemExit) as exc:
        _main(test_args)
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "escapes repository root" in captured.err
