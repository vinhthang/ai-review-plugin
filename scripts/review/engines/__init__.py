"""Reviewer engine factory and registry."""
import os
import sys
from typing import Optional
from review.engines.base import ReviewEngineAdapter
from review.engines.workbuddy import WorkBuddyAdapter
from review.engines.codex import CodexAdapter

def resolve_engine(
    cli_engine: Optional[str],
    cli_session_id: Optional[str]
) -> str:
    # 1. Session ID Prefix Binding
    if cli_session_id:
        if cli_session_id.startswith("workbuddy:"):
            if cli_engine and cli_engine != "workbuddy":
                print(f"Fatal: Mismatched engine '{cli_engine}' for session prefix 'workbuddy:'", file=sys.stderr)
                sys.exit(2)
            return "workbuddy"
        elif cli_session_id.startswith("codex:"):
            if cli_engine and cli_engine != "codex":
                print(f"Fatal: Mismatched engine '{cli_engine}' for session prefix 'codex:'", file=sys.stderr)
                sys.exit(2)
            return "codex"
        else:
            # Unprefixed legacy session
            if cli_engine:
                return cli_engine
            # Rule: Unprefixed legacy sessions authoritatively default to Codex
            return "codex"

    # 2. CLI flag
    if cli_engine:
        if cli_engine not in ("workbuddy", "codex"):
            print(f"Fatal: Unsupported review engine '{cli_engine}'. Supported engines: 'workbuddy', 'codex'.", file=sys.stderr)
            sys.exit(2)
        return cli_engine

    # 3. Environment Variable
    env_engine = os.environ.get("AI_REVIEW_ENGINE")
    if env_engine:
        if env_engine not in ("workbuddy", "codex"):
            print(f"Fatal: Unsupported review engine in AI_REVIEW_ENGINE '{env_engine}'. Supported engines: 'workbuddy', 'codex'.", file=sys.stderr)
            sys.exit(2)
        return env_engine

    # 4. Default: workbuddy
    return "workbuddy"


__all__ = [
    "ReviewEngineAdapter",
    "WorkBuddyAdapter",
    "CodexAdapter",
    "resolve_engine",
]
