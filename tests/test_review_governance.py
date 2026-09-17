import os
import json
import tempfile
import pytest
from review.governance import archive_review_artifact, update_index_catalog

def test_archive_review_artifact_increments_version(tmp_path):
    repo_root = str(tmp_path)
    feature_id = "test-feature"
    
    # Version 1
    p1 = archive_review_artifact(repo_root, feature_id, "spec", {"issues": []})
    assert os.path.basename(p1) == "spec-v1.json"
    assert os.path.exists(p1)

    # Version 2
    p2 = archive_review_artifact(repo_root, feature_id, "spec", {"issues": [{"severity": "P0"}]})
    assert os.path.basename(p2) == "spec-v2.json"
    assert os.path.exists(p2)

def test_update_index_catalog(tmp_path):
    repo_root = str(tmp_path)
    specs_dir = os.path.join(repo_root, "docs", "superpowers", "specs")
    os.makedirs(specs_dir, exist_ok=True)
    index_file = os.path.join(specs_dir, "INDEX.md")

    initial_index = """# Index
| Feature ID | Title | Status | Range | Summary | Spec Link |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `feature-alpha` | Feature Alpha | In Progress | `REQ-001` | Details | [`spec.md`](./feature-alpha/spec.md) |
"""
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(initial_index)

    success = update_index_catalog(repo_root, "feature-alpha", "Approved", "./feature-alpha/reviews/spec-v1.json")
    assert success is True

    with open(index_file, "r", encoding="utf-8") as f:
        updated = f.read()

    assert "Approved" in updated
    assert "./feature-alpha/reviews/spec-v1.json" in updated
