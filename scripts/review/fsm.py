"""Declarative Review Lifecycle Finite State Machine (Audit -> Remediation -> Governance)."""
from enum import Enum, auto
from typing import Any, Callable, Dict, Optional, Tuple

class ReviewState(Enum):
    INIT = auto()
    AUDIT = auto()
    REMEDIATION = auto()
    GOVERNANCE = auto()
    DONE = auto()
    ABORTED = auto()

class ReviewEvent(Enum):
    TARGET_VALIDATED = auto()          # 1. Target Validated
    VERDICT_CLEAN = auto()             # 1. Clean (Zero P0/P1)
    VERDICT_BLOCKED = auto()           # 2. Defects Found (P0/P1 present)
    VERDICT_FATAL = auto()             # 3c. Fatal System Error
    REMEDIATION_PATCHED = auto()       # 3. Re-Audit Loop (escalation_counter < 3)
    ESCALATION_LIMIT_REACHED = auto()  # 4. Escalated (escalation_counter >= 3)
    HUMAN_APPROVED = auto()            # 5. Approved ("Proceed")
    HUMAN_RETRY = auto()               # 6. Guided Retry (Resets counter)
    HUMAN_REJECTED = auto()            # 7. Rejected / Abort

class ReviewFSM:
    """Deterministic, Table-Driven Lifecycle FSM for AI Review Flows."""

    TRANSITIONS: Dict[Tuple[ReviewState, ReviewEvent], Tuple[ReviewState, Optional[Callable[[Dict[str, Any]], bool]]]] = {
        # INIT
        (ReviewState.INIT, ReviewEvent.TARGET_VALIDATED): (ReviewState.AUDIT, None),

        # AUDIT
        (ReviewState.AUDIT, ReviewEvent.VERDICT_CLEAN): (ReviewState.GOVERNANCE, None),
        (ReviewState.AUDIT, ReviewEvent.VERDICT_BLOCKED): (ReviewState.REMEDIATION, None),
        (ReviewState.AUDIT, ReviewEvent.VERDICT_FATAL): (ReviewState.ABORTED, None),

        # REMEDIATION
        (ReviewState.REMEDIATION, ReviewEvent.REMEDIATION_PATCHED): (
            ReviewState.AUDIT,
            lambda ctx: ctx.get("escalation_counter", 0) < 3,
        ),
        (ReviewState.REMEDIATION, ReviewEvent.ESCALATION_LIMIT_REACHED): (
            ReviewState.GOVERNANCE,
            lambda ctx: ctx.get("escalation_counter", 0) >= 3,
        ),

        # GOVERNANCE
        (ReviewState.GOVERNANCE, ReviewEvent.HUMAN_APPROVED): (ReviewState.DONE, None),
        (ReviewState.GOVERNANCE, ReviewEvent.HUMAN_RETRY): (ReviewState.AUDIT, None),
        (ReviewState.GOVERNANCE, ReviewEvent.HUMAN_REJECTED): (ReviewState.ABORTED, None),
    }

    def __init__(self, initial_state: ReviewState = ReviewState.INIT):
        self.state = initial_state

    def transition(self, event: ReviewEvent, context: Optional[Dict[str, Any]] = None) -> bool:
        """Execute a state transition based on the declarative transition table.
        
        Returns True if transition succeeded, False if invalid or guard failed.
        """
        entry = self.TRANSITIONS.get((self.state, event))
        if not entry:
            return False

        next_state, guard = entry
        ctx = context or {}
        if guard is not None and not guard(ctx):
            return False

        self.state = next_state
        return True
