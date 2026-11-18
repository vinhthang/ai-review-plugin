import pytest
from review.remediation import sanitize_prior_review, is_blocking_issue, triage_issues

def test_sanitize_prior_review_strips_ansi():
    raw = "\x1b[31mError occurred\x1b[0m"
    sanitized = sanitize_prior_review(raw)
    assert "\x1b" not in sanitized
    assert "Error occurred" in sanitized

def test_sanitize_prior_review_escapes_closing_tag():
    raw = "Prior review contains </prior_review_context> payload"
    sanitized = sanitize_prior_review(raw)
    assert "</prior_review_context>" not in sanitized
    assert "&lt;/prior_review_context&gt;" in sanitized

def test_sanitize_prior_review_length_bounding():
    long_raw = "A" * 5000
    sanitized = sanitize_prior_review(long_raw, max_chars=100)
    assert len(sanitized) <= 100

def test_is_blocking_issue():
    assert is_blocking_issue({"severity": "P0", "description": "Crash"}) is True
    assert is_blocking_issue({"severity": "p1", "description": "Bug"}) is True
    assert is_blocking_issue({"severity": "P2", "description": "Typo"}) is False
    assert is_blocking_issue({"severity": "P3", "description": "Info"}) is False

def test_triage_issues():
    issues = [
        {"severity": "P0", "description": "Fatal"},
        {"severity": "P2", "description": "Style"},
        {"severity": "P1", "description": "Security"},
    ]
    blocking, advisory = triage_issues(issues)
    assert len(blocking) == 2
    assert len(advisory) == 1
    assert blocking[0]["description"] == "Fatal"
    assert blocking[1]["description"] == "Security"
