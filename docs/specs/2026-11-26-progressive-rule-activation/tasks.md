# Tasks: Progressive `model_decision` Activation for `ai-review-plugin` Rules

Sources: [spec.md](./spec.md), [design.md](./design.md)

## Task 1: Replace `rules/AGENTS.md` with `rules/ai-review.md` and update tests

- [x] Complete the work and its applicable checks.
- Covers: REQ-058 / AC-058-1, AC-058-2
- Files: `rules/ai-review.md`, `rules/AGENTS.md`, `tests/test_harness2_review.py`, `tests/test_prepare_code_review.py`
- Dependencies: None
- Blocked by: None
- Work: Create `rules/ai-review.md` (`trigger: model_decision`), delete `rules/AGENTS.md`, update `tests/test_harness2_review.py` and `tests/test_prepare_code_review.py`, and verify with `surface_validator.py` and `pytest`.
- Completion evidence: Verified in [Run 1](./verification.md#run-1--2026-11-26).

## Gate 2: traceability and readiness

| Requirement | AC | ADR or rationale | Design | Task | Planned verification | Status / reason |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-058 | AC-058-1 | [Rationale](./decisions.md#architectural-rationale) | [Components](./design.md#components) | [Task 1](#task-1-replace-rulesagentsmd-with-rulesai-reviewmd-and-update-tests) | [AC-058-1](./verification.md#ac-058-1-req-058) | PASS — `rules/ai-review.md` & `always_on_chars == 0` mapped |
| REQ-058 | AC-058-2 | [Rationale](./decisions.md#architectural-rationale) | [Boundaries](./design.md#boundaries-and-recovery) | [Task 1](#task-1-replace-rulesagentsmd-with-rulesai-reviewmd-and-update-tests) | [AC-058-2](./verification.md#ac-058-2-req-058) | PASS — missing description/triggers caught by `surface_validator.py` |

- Backward scope check: PASS — Task 1 serves strictly `REQ-058` (`AC-058-1`, `AC-058-2`).
- Reference and catalog consistency: PASS — all links, anchors, and `docs/specs/INDEX.md` entries match.
