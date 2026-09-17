"""Data contracts and envelope models for AI Review Plugin."""
import os
import sys
import json
import re
from enum import Enum, auto
from typing import List, Dict, Tuple, Optional, Any

class ReviewVerdict(Enum):
    CLEAN = auto()      # No P0/P1 issues detected
    BLOCKED = auto()    # P0/P1 defects found
    FATAL = auto()      # Unrecoverable or syntax error

Issue = Dict[str, Any]
ReviewEnvelope = Dict[str, Any]

SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["P0", "P1", "P2"]},
                    "description": {"type": "string", "minLength": 1}
                },
                "required": ["severity", "description"],
                "additionalProperties": False
            }
        }
    },
    "required": ["issues"],
    "additionalProperties": False
}

WORKBUDDY_MODEL_MAP = {
    "deepseek 4.1 flash": "deepseek-v4.1-flash",
    "deepseek-4.1-flash": "deepseek-v4.1-flash",
    "deepseek v4.1 flash": "deepseek-v4.1-flash",
    "deepseek-v4.1-flash": "deepseek-v4.1-flash",
    "deepseek": "deepseek-v4.1-flash",
    "flash": "deepseek-v4.1-flash",
    "fast": "deepseek-v4.1-flash",
    "fast-model": "deepseek-v4.1-flash",
    "balanced": "balanced-model",
    "balanced-model": "balanced-model",
    "primary": "primary-model",
    "primary-model": "primary-model",
    "deep": "deep-model",
    "deep-model": "deep-model",
}

def format_review_envelope(engine: str, session_id: str, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Construct standard review JSON envelope."""
    return {
        "issues": issues,
        "session_id": session_id,
        "engine": engine
    }


def sanitize_diagnostics(text: str, max_chars: int = 2000) -> str:
    if not text:
        return ""
    # Redact common credential patterns
    redacted = re.sub(
        r'(?i)(bearer\s+|token[=:\s]+|secret[=:\s]+|password[=:\s]+|key[=:\s]+)([a-zA-Z0-9_\-\.]{8,})',
        r'\1[REDACTED]',
        text
    )
    if len(redacted) > max_chars:
        return redacted[:max_chars] + "\n[... truncated diagnostic output ...]"
    return redacted
