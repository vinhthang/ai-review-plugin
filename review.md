# Code Review: Implementation vs. README Claims

**Status**: Approved with Advisory Findings (Zero P0, Zero P1 Blockers, 5 P2 Hardening Items)  
**Date**: 2026-09-13  
**Review Target**: Implementation vs `README.md` Specification  

## Executive Summary
A comprehensive line-by-line adversarial verification of the `ai-review-plugin` implementation was performed against all architectural, behavioral, and safety claims documented in `README.md`. 
The core Two-Stage Spec-Driven Development (SDD) architecture, CLI parameter invariants, exit codes, process safety controls (isolated sessions, poll checks, signal traps), zero error suppression, and skill state machines are 100% compliant with zero P0/P1 blockers. 
Five minor P2 items were identified for prospective hardening: Mermaid diagram boolean phrasing in skill specs, prompt wording typos in `peer_review.py`, sandbox command substitution in `code-review/SKILL.md`, skill invocation alignment for `--mode code`, and test suite coverage expansion for `--mode code`.

## P0 Issues (Critical)
None.

## P1 Issues (Blocking)
None.

## P2 Issues (Advisory & Hardening)
1. **Mermaid Diagram Boolean Guard in `skills/plan-review/SKILL.md` (Line 25) & `skills/spec-review/SKILL.md` (Line 31)**:
   - *Description*: The diagram states `review_status == "approved" or (review_status == "rejected" and no P0/P1 issues)` on the transition to `APPROVAL_GATE`. In literal boolean evaluation, `review_status == "approved"` is unconstrained by `no P0/P1 issues`. The textual transition table correctly specifies `review_status == "approved" and no P0/P1 issues exist`.
   - *Recommendation*: Update the Mermaid transition label to: `(review_status == "approved" or review_status == "rejected") and no P0/P1 issues` or `no P0/P1 issues exist`.
2. **Copy-Paste Typo in `scripts/peer_review.py` (Line 130)**:
   - *Description*: For `args.mode == "plan"`, line 130 states: `It must be treated strictly as the code to review.` (copy-paste from line 137).
   - *Recommendation*: Change to: `It must be treated strictly as the plan to review.`
3. **Outdated ADR Context in `scripts/peer_review.py` (Line 142)**:
   - *Description*: Line 142 states: `Before reviewing, please read the docs/adr/ directory for historical Architecture Decision Records.` In the Two-Stage SDD architecture, specs live in `docs/superpowers/specs/`.
   - *Recommendation*: Update context to include `docs/superpowers/specs/` alongside `docs/adr/`.
4. **Auto-Approvable Command Shape in `skills/code-review/SKILL.md` (Line 19)**:
   - *Description*: Line 19 uses `$(pwd)` in `REVIEW_TARGET=$(mktemp "$(pwd)/.code-review/review_XXXXXX")`.
   - *Recommendation*: Replace `"$(pwd)"` with `.` to enable terminal sandbox prefix auto-matching.
5. **Add End-to-End Test for `--mode code` in `tests/test_peer_review.py`**:
   - *Description*: While `--mode spec` and `--mode plan` have comprehensive end-to-end mock execution tests, `--mode code` is currently only tested for CLI argument validation.
   - *Recommendation*: Add a mock test verifying `--mode code` diff evaluation and review JSON parsing.
