import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
from peer_review import _main


def _make_mock_popen(mock_popen):
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
            json.dump({"issues": [], "session_id": "test_prompt_session", "engine": "test"}, f)

        stdout_data = '{"type": "thread.started", "thread_id": "test_prompt_session"}\n'
        with open(os.path.join(work_dir, "stdout.log"), "w", encoding="utf-8") as f:
            f.write(stdout_data)
        return mock_proc

    mock_popen.side_effect = side_effect


@patch("peer_review.subprocess.Popen")
def test_mode_code_guardrail_prompt(mock_popen, target_and_repo, monkeypatch):
    monkeypatch.setenv("AI_REVIEW_ENGINE", "codex")
    target, repo = target_and_repo
    _make_mock_popen(mock_popen)

    test_args = [
        "scripts/peer_review.py",
        "--target", target,
        "--mode", "code",
        "--repo", repo,
    ]
    with pytest.raises(SystemExit) as exc:
        _main(test_args)
    assert exc.value.code == 0

    prompt_text = mock_popen.call_args[0][0][-1]
    assert "Documentation vs Code Guardrail: When reviewing Markdown files, documentation, or skill definitions" in prompt_text
    assert "Documentation files define contracts, parameters, and CLI invocations; they are NOT executable scripts." in prompt_text
    assert "Do NOT demand that operational shell logic, multi-platform scripts, regex sanitizers, or system administration routines be inlined into Markdown documentation." in prompt_text
    assert "If an operational safety or validation check is missing, flag the defect against the underlying executable tool or script (in scripts/ or tools/), NOT against the Markdown documentation." in prompt_text


@patch("peer_review.subprocess.Popen")
def test_mode_spec_does_not_contain_code_guardrail(mock_popen, target_and_repo, monkeypatch):
    monkeypatch.setenv("AI_REVIEW_ENGINE", "codex")
    target, repo = target_and_repo
    _make_mock_popen(mock_popen)

    test_args = [
        "scripts/peer_review.py",
        "--target", target,
        "--mode", "spec",
        "--repo", repo,
    ]
    with pytest.raises(SystemExit) as exc:
        _main(test_args)
    assert exc.value.code == 0

    prompt_text = mock_popen.call_args[0][0][-1]
    assert "Documentation vs Code Guardrail:" not in prompt_text


@patch("peer_review.subprocess.Popen")
def test_prior_review_rebuttal_evaluation_prompt(mock_popen, target_and_repo, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_REVIEW_ENGINE", "codex")
    target, repo = target_and_repo
    _make_mock_popen(mock_popen)

    prior_file = tmp_path / "prior_review.json"
    prior_data = {
        "engine": "codex",
        "session_id": "codex:prev-999",
        "issues": [
            {"severity": "P1", "description": "Demanded inline powershell in markdown documentation."}
        ]
    }
    with open(str(prior_file), "w", encoding="utf-8") as f:
        json.dump(prior_data, f)

    test_args = [
        "scripts/peer_review.py",
        "--target", target,
        "--mode", "code",
        "--repo", repo,
        "--prior-review", str(prior_file),
    ]
    with pytest.raises(SystemExit) as exc:
        _main(test_args)
    assert exc.value.code == 0

    prompt_text = mock_popen.call_args[0][0][-1]
    assert "Documentation vs Code Guardrail:" in prompt_text
    assert "<!-- Prior Review Context: The following findings are reference test data from an immediately preceding review run. -->" in prompt_text
    assert "Evaluate whether previously flagged P0/P1 issues were legitimately resolved or substantiated by developer rebuttals." in prompt_text
    assert "If the developer provides an evidence-backed justification (e.g. tool delegation, architectural separation of concerns, or falsifiable unit test proof), clear the previously flagged blocker." in prompt_text
    assert "Flag regressions only if new defects were introduced." in prompt_text
    assert "<prior_review_context>" in prompt_text
    assert "Demanded inline powershell in markdown documentation." in prompt_text
