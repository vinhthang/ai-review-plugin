"""Governance Stage: Semantic review archival and central cataloging."""
import os
import json
import re
from typing import Dict, Any, Optional

def archive_review_artifact(repo_root: str, feature_id: str, mode: str, review_data: Dict[str, Any]) -> str:
    """Archive review artifact to docs/superpowers/specs/<feature-id>/reviews/<mode>-v<N>.json."""
    pkg_reviews_dir = os.path.join(repo_root, "docs", "superpowers", "specs", feature_id, "reviews")
    os.makedirs(pkg_reviews_dir, exist_ok=True)

    # Calculate next version
    existing = os.listdir(pkg_reviews_dir)
    pattern = re.compile(rf"^{re.escape(mode)}-v(\d+)\.json$")
    versions = [int(m.group(1)) for f in existing if (m := pattern.match(f))]
    next_ver = max(versions, default=0) + 1

    dest_filename = f"{mode}-v{next_ver}.json"
    dest_path = os.path.join(pkg_reviews_dir, dest_filename)
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(review_data, f, indent=2)

    return dest_path

def update_index_catalog(repo_root: str, feature_id: str, status: str, review_link: str) -> bool:
    """Update docs/superpowers/specs/INDEX.md with updated review link and status."""
    index_path = os.path.join(repo_root, "docs", "superpowers", "specs", "INDEX.md")
    if not os.path.isfile(index_path):
        return False

    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Match row starting with feature_id
    pattern = re.compile(rf"^\|\s*`{re.escape(feature_id)}`\s*\|.*$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return False

    row = match.group(0)
    cols = [col.strip() for col in row.split("|")[1:-1]]
    if len(cols) >= 6:
        cols[2] = status
        cols[5] = f"[{cols[5].split(']')[0][1:]}]({review_link})"
        new_row = "| " + " | ".join(cols) + " |"
        content = content[:match.start()] + new_row + content[match.end():]
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False
