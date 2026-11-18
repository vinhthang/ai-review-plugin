"""Reviewer engine factory and registry."""
import os
import sys
from typing import Optional, Dict, Type, List
from review.engines.base import ReviewEngineAdapter
from review.engines.workbuddy import WorkBuddyAdapter
from review.engines.codex import CodexAdapter
from review.engines.argon import ArgonWebAdapter

ENGINE_REGISTRY: Dict[str, Type[ReviewEngineAdapter]] = {
    "workbuddy": WorkBuddyAdapter,
    "codex": CodexAdapter,
    "argon-web": ArgonWebAdapter,
}

ENGINE_SESSION_PREFIXES: Dict[str, str] = {
    "workbuddy:": "workbuddy",
    "codex:": "codex",
    "argon-web:": "argon-web",
}

def register_engine(name: str, adapter_cls: Type[ReviewEngineAdapter]) -> None:
    """Register an engine adapter class under the specified name."""
    ENGINE_REGISTRY[name] = adapter_cls

def get_engine_adapter(name: str) -> ReviewEngineAdapter:
    """Instantiate and return the engine adapter registered for name."""
    if name not in ENGINE_REGISTRY:
        raise ValueError(f"Unsupported review engine: {name}")
    return ENGINE_REGISTRY[name]()

def get_supported_engines() -> List[str]:
    """Return sorted list of all registered engine identifiers."""
    return sorted(list(ENGINE_REGISTRY.keys()))

def resolve_engine(
    cli_engine: Optional[str],
    cli_session_id: Optional[str]
) -> str:
    supported = get_supported_engines()

    # 1. Session ID Prefix Binding
    if cli_session_id:
        matched_engine = None
        matched_prefix = None
        for prefix, engine_name in ENGINE_SESSION_PREFIXES.items():
            if cli_session_id.startswith(prefix):
                matched_engine = engine_name
                matched_prefix = prefix
                break

        if matched_engine:
            if cli_engine and cli_engine != matched_engine:
                print(f"Fatal: Mismatched engine '{cli_engine}' for session prefix '{matched_prefix}'", file=sys.stderr)
                sys.exit(2)
            return matched_engine
        else:
            # Unprefixed legacy session
            if cli_engine:
                if cli_engine not in supported:
                    print(f"Fatal: Unsupported review engine '{cli_engine}'. Supported engines: {', '.join(repr(s) for s in supported)}.", file=sys.stderr)
                    sys.exit(2)
                return cli_engine
            # Rule: Unprefixed legacy sessions authoritatively default to Codex
            return "codex"

    # 2. CLI flag
    if cli_engine:
        if cli_engine not in supported:
            print(f"Fatal: Unsupported review engine '{cli_engine}'. Supported engines: {', '.join(repr(s) for s in supported)}.", file=sys.stderr)
            sys.exit(2)
        return cli_engine

    # 3. Environment Variable
    env_engine = os.environ.get("AI_REVIEW_ENGINE")
    if env_engine:
        if env_engine not in supported:
            print(f"Fatal: Unsupported review engine in AI_REVIEW_ENGINE '{env_engine}'. Supported engines: {', '.join(repr(s) for s in supported)}.", file=sys.stderr)
            sys.exit(2)
        return env_engine

    # 4. Default: workbuddy
    return "workbuddy"


__all__ = [
    "ReviewEngineAdapter",
    "WorkBuddyAdapter",
    "CodexAdapter",
    "ArgonWebAdapter",
    "ENGINE_REGISTRY",
    "ENGINE_SESSION_PREFIXES",
    "register_engine",
    "get_engine_adapter",
    "get_supported_engines",
    "resolve_engine",
]
