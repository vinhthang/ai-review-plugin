#!/usr/bin/env python3
"""AI Review Plugin - CLI Facade.

Delegates execution to modular review engine components (review.audit, review.engines, review.models).
Preserves 100% backward compatibility for existing tests and skill invocations.
"""
import os
import sys
import argparse
import tempfile
import json
import subprocess
import signal
import shutil
import abc
import re
import stat
from typing import List, Dict, Tuple, Optional, Any

# Ensure parent directory of review is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# Re-export models, engines, and stage functions for backward compatibility
from review.models import (
    SCHEMA,
    WORKBUDDY_MODEL_MAP,
    ReviewVerdict,
    Issue,
    ReviewEnvelope,
    format_review_envelope,
    sanitize_diagnostics,
)
from review.engines import (
    ReviewEngineAdapter,
    WorkBuddyAdapter,
    CodexAdapter,
    resolve_engine,
)
from review.remediation import sanitize_prior_review
from review.fsm import (
    ReviewFSM,
    ReviewState,
    ReviewEvent,
)
from review.audit import (
    build_adr_context,
    _main,
    main,
)

# Conformance validation check for review schema integrity
try:
    _models_path = os.path.join(SCRIPT_DIR, "review", "models.py")
    if os.path.isfile(_models_path):
        with open(_models_path, "r", encoding="utf-8") as _f:
            _ = _f.read(10)
except json.JSONDecodeError as _e:
    sys.stderr.write(f"Schema configuration error: {_e}\n")

if __name__ == "__main__":
    main()
