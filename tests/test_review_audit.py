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

@patch("peer_review.subprocess.Popen")
def test_mode_spec_valid_execution(mock_run, target_and_repo, capsys):
    target, repo = target_and_repo
    
    def side_effect(cmd, **kwargs):
        if cmd[0] != "codex":
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.poll.return_value = 0
            mock_proc.wait.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.__enter__.return_value = mock_proc
            return mock_proc
        
        prompt_text = cmd[-1]
        assert "architectural design, problem framing, invariants, boundary contracts" in prompt_text
        assert "zero placeholders (no TODO/TBD)" in prompt_text
        
        schema_idx = cmd.index("--output-schema")
        schema_path = cmd[schema_idx + 1]
        work_dir = os.path.dirname(schema_path)
        review_file = os.path.join(work_dir, "review.json")
        with open(review_file, 'w', encoding="utf-8") as f:
            json.dump({"issues": []}, f)
        
        with open(os.path.join(work_dir, "stdout.log"), 'w', encoding="utf-8") as f:
            f.write('{"type": "thread.started", "thread_id": "spec_session_123"}\n')
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"", b"")
        return mock_proc

    mock_run.side_effect = side_effect

    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "spec", "--repo", repo]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 0
        captured = capsys.readouterr()
        output_json = json.loads(captured.out)
        assert output_json["session_id"] == "spec_session_123"
        assert output_json["issues"] == []

@patch("peer_review.subprocess.Popen")
def test_mode_spec_rejection(mock_run, target_and_repo):
    target, repo = target_and_repo
    
    def side_effect(cmd, **kwargs):
        if cmd[0] != "codex":
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.poll.return_value = 0
            mock_proc.wait.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.__enter__.return_value = mock_proc
            return mock_proc
        
        schema_idx = cmd.index("--output-schema")
        schema_path = cmd[schema_idx + 1]
        work_dir = os.path.dirname(schema_path)
        review_file = os.path.join(work_dir, "review.json")
        with open(review_file, 'w', encoding="utf-8") as f:
            json.dump({"issues": [{"severity": "P1", "description": "missing error boundaries"}]}, f)
        
        with open(os.path.join(work_dir, "stdout.log"), 'w', encoding="utf-8") as f:
            f.write('{"type": "thread.started", "thread_id": "spec_session_123"}\n')
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"", b"")
        return mock_proc

    mock_run.side_effect = side_effect

    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "spec", "--repo", repo]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 1

@patch("peer_review.subprocess.Popen")
def test_mode_design_with_valid_spec(mock_run, target_and_repo, spec_file):
    target, repo = target_and_repo
    
    def side_effect(cmd, **kwargs):
        if cmd[0] != "codex":
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.poll.return_value = 0
            mock_proc.wait.return_value = 0
            mock_proc.communicate.return_value = (b"", b"")
            mock_proc.__enter__.return_value = mock_proc
            return mock_proc
        
        prompt_text = cmd[-1]
        assert "Governing Specification: Compare this plan against the specification at" in prompt_text
        assert "Every requirement and invariant in the spec must be addressed" in prompt_text
        
        schema_idx = cmd.index("--output-schema")
        schema_path = cmd[schema_idx + 1]
        work_dir = os.path.dirname(schema_path)
        spec_copy = os.path.join(work_dir, "spec.file")
        assert os.path.isfile(spec_copy), "spec.file must be copied into sandbox"
        
        review_file = os.path.join(work_dir, "review.json")
        with open(review_file, 'w', encoding="utf-8") as f:
            json.dump({"issues": []}, f)
        with open(os.path.join(work_dir, "stdout.log"), 'w', encoding="utf-8") as f:
            f.write('{"type": "thread.started", "thread_id": "design_spec_session"}\n')
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (b"", b"")
        return mock_proc

    mock_run.side_effect = side_effect

    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "design", "--repo", repo, "--spec", spec_file]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 0

def test_mode_design_with_missing_spec_file_exits_2(target_and_repo, capsys):
    target, repo = target_and_repo
    nonexistent = "/nonexistent/path/to/spec.md"
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "design", "--repo", repo, "--spec", nonexistent]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 2
        captured = capsys.readouterr()
        assert f"Fatal: spec file does not exist: {nonexistent}" in captured.err

def test_mode_design_missing_spec_and_no_spec_exits_2(target_and_repo, capsys):
    target, repo = target_and_repo
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "design", "--repo", repo]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 2
        captured = capsys.readouterr()
        assert "Fatal: --mode design requires either --spec <path> or --no-spec." in captured.err

def test_spec_and_no_spec_mutual_exclusion_exits_2(target_and_repo, spec_file, capsys):
    target, repo = target_and_repo
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "design", "--repo", repo, "--spec", spec_file, "--no-spec"]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 2
        captured = capsys.readouterr()
        assert "Fatal: --spec and --no-spec are mutually exclusive." in captured.err

def test_mode_spec_with_spec_flag_forbidden_exits_2(target_and_repo, spec_file, capsys):
    target, repo = target_and_repo
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "spec", "--repo", repo, "--spec", spec_file]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 2
        captured = capsys.readouterr()
        assert "Fatal: --spec cannot be used with --mode spec." in captured.err

def test_mode_spec_with_no_spec_flag_forbidden_exits_2(target_and_repo, capsys):
    target, repo = target_and_repo
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "spec", "--repo", repo, "--no-spec"]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 2
        captured = capsys.readouterr()
        assert "Fatal: --no-spec cannot be used with --mode spec." in captured.err

def test_mode_code_with_spec_flag_forbidden_exits_2(target_and_repo, spec_file, capsys):
    target, repo = target_and_repo
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "code", "--repo", repo, "--spec", spec_file]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 2
        captured = capsys.readouterr()
        assert "Fatal: --spec cannot be used with --mode code." in captured.err

def test_mode_code_with_no_spec_flag_forbidden_exits_2(target_and_repo, capsys):
    target, repo = target_and_repo
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "code", "--repo", repo, "--no-spec"]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 2
        captured = capsys.readouterr()
        assert "Fatal: --no-spec cannot be used with --mode code." in captured.err

@patch("peer_review.subprocess.Popen")
def test_design_mode_prompt_target_wording(mock_run, target_and_repo):
    target, repo = target_and_repo
    def side_effect(cmd, **kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "codex":
            work_dir = os.path.dirname(cmd[cmd.index("-o") + 1])
            with open(os.path.join(work_dir, "review.json"), "w", encoding="utf-8") as f:
                json.dump({"issues": []}, f)
            kwargs["stdout"].write(json.dumps({"type": "thread.started", "thread_id": "t1"}) + "\n")
        proc = MagicMock()
        proc.poll.return_value = 0
        proc.returncode = 0
        proc.wait.return_value = 0
        proc.communicate.return_value = ("", "")
        proc.__enter__.return_value = proc
        return proc
    mock_run.side_effect = side_effect
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "design", "--repo", repo, "--no-spec"]):
        with pytest.raises(SystemExit) as exc_info:
            peer_review.main()
        assert exc_info.value.code == 0
    cmd = mock_run.call_args[0][0]
    prompt = cmd[-1]
    assert "strictly as the plan to review" in prompt
    assert "strictly as the code to review" not in prompt


@patch("peer_review.subprocess.Popen")
def test_prompt_specs_context_conditional(mock_run, target_and_repo, spec_file):
    target, repo = target_and_repo
    diff_file = os.path.join(repo, "changes.diff")
    with open(diff_file, "w", encoding="utf-8") as f:
        f.write("--- a/f\n+++ b/f\n")
    def side_effect(cmd, **kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "codex":
            work_dir = os.path.dirname(cmd[cmd.index("-o") + 1])
            with open(os.path.join(work_dir, "review.json"), "w", encoding="utf-8") as f:
                json.dump({"issues": []}, f)
            kwargs["stdout"].write(json.dumps({"type": "thread.started", "thread_id": "t1"}) + "\n")
        proc = MagicMock()
        proc.poll.return_value = 0
        proc.returncode = 0
        proc.wait.return_value = 0
        proc.communicate.return_value = ("", "")
        proc.__enter__.return_value = proc
        return proc
    mock_run.side_effect = side_effect
    
    # Test 1: plan mode with --spec includes specs directory
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "design", "--repo", repo, "--spec", spec_file]):
        with pytest.raises(SystemExit):
            peer_review.main()
    prompt_with_spec = mock_run.call_args[0][0][-1]
    assert "docs/superpowers/specs/" in prompt_with_spec
    
    # Test 2: plan mode with --no-spec excludes specs directory
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "design", "--repo", repo, "--no-spec"]):
        with pytest.raises(SystemExit):
            peer_review.main()
    prompt_no_spec = mock_run.call_args[0][0][-1]
    assert "docs/superpowers/specs/" not in prompt_no_spec
    
    # Test 3: spec mode excludes docs/superpowers/specs/ (spec is the target itself)
    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "spec", "--repo", repo]):
        with pytest.raises(SystemExit):
            peer_review.main()
    prompt_spec_mode = mock_run.call_args[0][0][-1]
    assert "docs/superpowers/specs/" not in prompt_spec_mode

    # Test 4: code mode excludes docs/superpowers/specs/ (spec flag is forbidden)
    with patch("sys.argv", ["peer_review.py", "--target", diff_file, "--mode", "code", "--repo", repo]):
        with pytest.raises(SystemExit):
            peer_review.main()
    prompt_code_mode = mock_run.call_args[0][0][-1]
    assert "docs/superpowers/specs/" not in prompt_code_mode



@patch("peer_review.subprocess.Popen")
def test_mode_code_valid_execution(mock_run, target_and_repo, capsys):
    target, repo = target_and_repo
    diff_file = os.path.join(repo, "changes.diff")
    test_diff_content = "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new\n"
    with open(diff_file, "w", encoding="utf-8") as f:
        f.write(test_diff_content)
    
    captured_copied_target = []
    def side_effect(cmd, **kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "codex":
            work_dir = os.path.dirname(cmd[cmd.index("-o") + 1])
            target_copy_path = os.path.join(work_dir, "target.file")
            if os.path.exists(target_copy_path):
                with open(target_copy_path, "r", encoding="utf-8") as tf:
                    captured_copied_target.append(tf.read())
            review_file = os.path.join(work_dir, "review.json")
            with open(review_file, "w", encoding="utf-8") as f:
                json.dump({"issues": []}, f)
            stdout_f = kwargs.get("stdout")
            if stdout_f:
                stdout_f.write(json.dumps({"type": "thread.started", "thread_id": "mock_code_thread_123"}) + "\n")
                stdout_f.flush()
        proc = MagicMock()
        proc.poll.return_value = 0
        proc.returncode = 0
        proc.wait.return_value = 0
        proc.communicate.return_value = ("", "")
        proc.__enter__.return_value = proc
        return proc
    mock_run.side_effect = side_effect

    with patch("sys.argv", ["peer_review.py", "--target", diff_file, "--mode", "code", "--repo", repo]):
        with pytest.raises(SystemExit) as exc_info:
            peer_review.main()
        assert exc_info.value.code == 0
    
    # Verify prompt construction contract
    cmd = mock_run.call_args[0][0]
    prompt = cmd[-1]
    assert "Perform a code review of this file:" in prompt
    assert "Focus on code-level issues, logic, and correctness." in prompt
    assert "Governing Specification:" not in prompt
    assert "Standalone Design Review:" not in prompt
    
    # Verify diff content was preserved in target copy
    assert len(captured_copied_target) == 1
    assert captured_copied_target[0] == test_diff_content

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["session_id"] == "mock_code_thread_123"
    assert len(data["issues"]) == 0





# ==============================================================================
# WorkBuddy AI Review Engine Test Suite
# ==============================================================================


def test_adr_payload_size_guard_truncates_adr_preserves_target(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    adr_dir = repo / "docs" / "adr"
    adr_dir.mkdir(parents=True)

    target_text = "T" * 50_000
    spec_text = "S" * 50_000

    # Create 5 ADRs with 100,000 characters each = 500,000 chars of ADRs
    # Total context = 50k + 50k + 500k = 600,000 > 500,000
    for i in range(1, 6):
        (adr_dir / f"000{i}-decision.md").write_text(f"HEADER_{i}\n" + ("X" * 99_980))

    # Should trigger size guard and warning
    adr_context = peer_review.build_adr_context(str(repo), target_text, spec_text, max_chars=500_000)

    _, err = capsys.readouterr()
    assert "Warning: Embedded prompt context exceeds 500,000 characters. Truncating surrounding ADR context." in err

    # Ensure target and spec + adr_context <= 500,000
    assert len(target_text) + len(spec_text) + len(adr_context) <= 500_000

    # Ensure newest ADRs are prioritized over older ones (0005 should be present, 0001 dropped)
    assert "HEADER_5" in adr_context
    assert "HEADER_1" not in adr_context



@patch("peer_review.subprocess.Popen")
def test_spec_mode_prompt_includes_build_ready_check(mock_run, target_and_repo):
    """Test that spec-mode peer review prompt embeds the 8-Question Build-Ready Check."""
    def side_effect(cmd, **kwargs):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.poll.return_value = 0
        mock_proc.wait.return_value = 0
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.__enter__.return_value = mock_proc

        if isinstance(cmd, list) and "-o" in cmd:
            work_dir = os.path.dirname(cmd[cmd.index("-o") + 1])
            with open(os.path.join(work_dir, "stdout.log"), 'w', encoding="utf-8") as f:
                f.write('{"type": "thread.started", "thread_id": "spec_session_123"}\n')
            with open(os.path.join(work_dir, "review.json"), 'w', encoding="utf-8") as f:
                json.dump({"issues": []}, f)
        return mock_proc
    mock_run.side_effect = side_effect

    target, repo = target_and_repo
    with patch("sys.argv", ["peer_review.py", "--target", str(target), "--mode", "spec", "--repo", str(repo)]):
        with pytest.raises(SystemExit) as exc_info:
            peer_review.main()

    assert exc_info.value.code == 0
    codex_calls = [c for c in mock_run.call_args_list if isinstance(c[0][0], list) and "-o" in c[0][0]]
    assert len(codex_calls) > 0
    prompt = codex_calls[0][0][0][-1]
    assert "Evaluate against the Build-Ready Specification Standard" in prompt
    assert "1. Consequential ambiguity" in prompt
    assert "2. Testable pass/fail" in prompt
    assert "clear separation of observable contracts from internal implementation details" in prompt



# --- Prior Review & Path Safety Tests ---
