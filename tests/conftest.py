import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

@pytest.fixture(autouse=True)
def _default_legacy_codex_engine(monkeypatch):
    if "AI_REVIEW_ENGINE" not in os.environ:
        monkeypatch.setenv("AI_REVIEW_ENGINE", "codex")

@pytest.fixture
def target_and_repo():
    with tempfile.NamedTemporaryFile(delete=False) as t_file:
        t_file.write(b"target content")
        target_path = t_file.name
        
    with tempfile.TemporaryDirectory() as repo_path:
        yield target_path, repo_path
        
    os.remove(target_path)

@pytest.fixture
def spec_file():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".md") as s_file:
        s_file.write(b"# Test Specification\nContext and invariants.")
        spec_path = s_file.name
    yield spec_path
    if os.path.exists(spec_path):
        os.remove(spec_path)
