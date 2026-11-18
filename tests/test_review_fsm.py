import pytest
from review.fsm import ReviewFSM, ReviewState, ReviewEvent

def test_fsm_initial_state():
    fsm = ReviewFSM()
    assert fsm.state == ReviewState.INIT

def test_fsm_valid_lifecycle_clean():
    fsm = ReviewFSM()
    assert fsm.transition(ReviewEvent.TARGET_VALIDATED) is True
    assert fsm.state == ReviewState.AUDIT

    assert fsm.transition(ReviewEvent.VERDICT_CLEAN) is True
    assert fsm.state == ReviewState.GOVERNANCE

    assert fsm.transition(ReviewEvent.HUMAN_APPROVED) is True
    assert fsm.state == ReviewState.DONE

def test_fsm_remediation_loop_under_ceiling():
    fsm = ReviewFSM()
    fsm.transition(ReviewEvent.TARGET_VALIDATED)
    assert fsm.state == ReviewState.AUDIT

    assert fsm.transition(ReviewEvent.VERDICT_BLOCKED) is True
    assert fsm.state == ReviewState.REMEDIATION

    # Attempt 1 -> loop back to AUDIT
    assert fsm.transition(ReviewEvent.REMEDIATION_PATCHED, context={"escalation_counter": 1}) is True
    assert fsm.state == ReviewState.AUDIT

def test_fsm_escalation_ceiling_reaches_governance():
    fsm = ReviewFSM()
    fsm.transition(ReviewEvent.TARGET_VALIDATED)
    fsm.transition(ReviewEvent.VERDICT_BLOCKED)
    assert fsm.state == ReviewState.REMEDIATION

    # Escalation counter >= 3 forces escalation to GOVERNANCE
    assert fsm.transition(ReviewEvent.ESCALATION_LIMIT_REACHED, context={"escalation_counter": 3}) is True
    assert fsm.state == ReviewState.GOVERNANCE

def test_fsm_human_retry_resets_to_audit():
    fsm = ReviewFSM(initial_state=ReviewState.GOVERNANCE)
    assert fsm.transition(ReviewEvent.HUMAN_RETRY) is True
    assert fsm.state == ReviewState.AUDIT

def test_fsm_human_rejected_aborts():
    fsm = ReviewFSM(initial_state=ReviewState.GOVERNANCE)
    assert fsm.transition(ReviewEvent.HUMAN_REJECTED) is True
    assert fsm.state == ReviewState.ABORTED

def test_fsm_invalid_transition_returns_false():
    fsm = ReviewFSM(initial_state=ReviewState.INIT)
    # Cannot go directly from INIT to DONE
    assert fsm.transition(ReviewEvent.HUMAN_APPROVED) is False
    assert fsm.state == ReviewState.INIT
