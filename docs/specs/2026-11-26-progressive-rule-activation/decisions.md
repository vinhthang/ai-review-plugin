# Decisions: Progressive `model_decision` Activation for `ai-review-plugin` Rules

Governing specification: [spec.md](./spec.md)

## Architectural rationale

- Governs: REQ-058

Because `2026-11-18-single-agent-code-review` carries `First entered In-Testing: 2026-11-18`, its `REQ-054` text is frozen. Antigravity's rules engine treats `rules/AGENTS.md` as unconditionally active, whereas `rules/ai-review.md` with YAML frontmatter `trigger: model_decision` enables progressive disclosure (`0` always-on tokens during unrelated coding turns) while preserving all governance invariants and triggers when review tasks arise.

## Gate 1: normative review

| Check | Status | Evidence / required correction |
| --- | --- | --- |
| Codebase grounding | PASS | Inspected `rules/AGENTS.md`, `tests/test_harness2_review.py`, `tests/test_prepare_code_review.py`, and `surface_validator.py`. |
| Attributable intent and explicit scope | PASS | Directly implements user's approved full `0`-always-on plan. |
| Observable requirements and meaningful acceptance criteria | PASS | `REQ-058` defines deterministic `AC-058-1` and `AC-058-2`. |
| Assumptions and owner-deferred questions are explicit | PASS | None open. |
| Architectural rationale respects requirements | PASS | Uses linked delta package instead of mutating frozen `REQ-054`. |
| IDs, references, and revision route are consistent | PASS | Allocates `REQ-058` above `REQ-057` cleanly in `docs/specs/INDEX.md`. |
