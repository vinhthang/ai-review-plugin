"""Remediation Stage: Issue triage and stateless rebuttal sanitization."""
import re
from typing import List, Dict, Any, Tuple

def sanitize_prior_review(content: str, max_chars: int = 2500) -> str:
    """Sanitizes and bounds prior review text to prevent prompt injection and context bloat."""
    if not content:
        return ""
    cleaned = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', content)
    cleaned = "".join(ch for ch in cleaned if ch in ('\n', '\t') or (ord(ch) >= 32 and ord(ch) != 127))
    cleaned = cleaned.replace("</prior_review_context>", "&lt;/prior_review_context&gt;")
    if len(cleaned) > max_chars:
        suffix = "... [truncated]"
        cleaned = cleaned[: max_chars - len(suffix)] + suffix
    return cleaned


def is_blocking_issue(issue: Dict[str, Any]) -> bool:
    """Determine if an issue is a blocking defect (P0 or P1)."""
    severity = str(issue.get("severity", "")).upper()
    return severity in ("P0", "P1")

def triage_issues(issues: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Triage issues into blocking defects (P0/P1) and non-blocking advisories (P2/P3)."""
    blocking = [i for i in issues if is_blocking_issue(i)]
    advisory = [i for i in issues if not is_blocking_issue(i)]
    return blocking, advisory
