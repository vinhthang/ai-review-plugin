import os
import sys
import tempfile
import json
import pytest
from unittest.mock import patch, MagicMock

# Add scripts directory to sys.path to import peer_review
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))
import peer_review

@pytest.fixture
def target_and_repo():
    with tempfile.NamedTemporaryFile(delete=False) as t_file:
        t_file.write(b"target content")
        target_path = t_file.name
        
    with tempfile.TemporaryDirectory() as repo_path:
        yield target_path, repo_path
        
    os.remove(target_path)

@patch("peer_review.subprocess.run")
def test_initial_state_and_success(mock_run, target_and_repo):
    target, repo = target_and_repo
    
    def side_effect(cmd, **kwargs):
        # We need to create review.json in work_dir which is passed via cmd for attempt 2,
        # but for attempt 1 it's in the same dir as schema_path
        schema_idx = cmd.index("--output-schema")
        schema_path = cmd[schema_idx + 1]
        work_dir = os.path.dirname(schema_path)
        review_file = os.path.join(work_dir, "review.json")
        with open(review_file, 'w') as f:
            json.dump({"issues": [{"severity": "P2", "description": "looks good"}]}, f)
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        return mock_proc

    mock_run.side_effect = side_effect

    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "plan", "--repo", repo]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        
        assert e.value.code == 0

@patch("peer_review.subprocess.run")
def test_state_transitions(mock_run, target_and_repo):
    target, repo = target_and_repo
    
    def side_effect(cmd, **kwargs):
        schema_idx = cmd.index("--output-schema")
        schema_path = cmd[schema_idx + 1]
        work_dir = os.path.dirname(schema_path)
        review_file = os.path.join(work_dir, "review.json")
        with open(review_file, 'w') as f:
            json.dump({"issues": [{"severity": "P1", "description": "bad"}]}, f)
        
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        return mock_proc

    mock_run.side_effect = side_effect

    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "plan", "--repo", repo]):
        with patch("sys.stdout", MagicMock()) as mock_stdout:
            with pytest.raises(SystemExit) as e:
                peer_review.main()
            assert e.value.code == 1
            # Retrieve work_dir from stdout
            mock_stdout.flush.assert_called()

@patch("sys.argv", ["peer_review.py", "--target", "dummy", "--mode", "plan", "--repo", "dummy", "--work-dir", "/invalid/path"])
def test_invalid_work_dir():
    with pytest.raises(SystemExit) as e:
        peer_review.main()
    assert e.value.code == 2

@patch("peer_review.subprocess.run")
def test_missing_schema_or_review_json(mock_run, target_and_repo):
    target, repo = target_and_repo
    
    def side_effect(cmd, **kwargs):
        # Do not create review.json
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        return mock_proc

    mock_run.side_effect = side_effect

    with patch("sys.argv", ["peer_review.py", "--target", target, "--mode", "plan", "--repo", repo]):
        with pytest.raises(SystemExit) as e:
            peer_review.main()
        assert e.value.code == 2
