# Progressive `model_decision` Activation for `ai-review-plugin` Rules

- Feature ID: 2026-11-26-progressive-rule-activation
- Type: enhancement
- Status: In-Testing
- First entered In-Testing: 2026-11-26
- Related specifications: Implemented: Changes [2026-11-18-single-agent-code-review](../2026-11-18-single-agent-code-review/spec.md), [2026-10-20-harness2-sandbox-and-inv-dom-review](../2026-10-20-harness2-sandbox-and-inv-dom-review/spec.md)

## Problem and source intent

User request: `/grill-me /plan do a deep review to my rules and skills, use knowledge from that github repository to enhance them`, followed by explicit selection of full `0`-always-on domain plugin conversion (`rules/ai-review.md` with `trigger: model_decision` + spec/test updates + commit/push).

Grounding against `2026-11-18-single-agent-code-review` (`REQ-054`), `rules/AGENTS.md` (`1,707` chars), `tests/test_harness2_review.py`, and `tests/test_prepare_code_review.py` showed that `rules/AGENTS.md` loads unconditionally on every Antigravity conversation turn—even when no code, spec, or design review is occurring.

## Repository grounding

- `rules/AGENTS.md`: `1,707`-char always-on rule defining `<rule name="ai-review-governance">` and triggers for `spec-review`, `design-review`, and `code-review`.
- `attention-guard/scripts/surface_validator.py`: Now supports Antigravity 2.4 frontmatter (`trigger: model_decision` with non-empty `description:`), reporting `always_on_chars == 0` when no unconditional rule files are present.
- `tests/test_harness2_review.py` & `tests/test_prepare_code_review.py`: Previously hardcoded `rules/AGENTS.md`.

## Non-goals

- Changing `skills/code-review/SKILL.md`, `skills/spec-review/SKILL.md`, `skills/design-review/SKILL.md`, or `scripts/review/*`.

## Requirements

### REQ-058: Progressive `model_decision` rule activation (`rules/ai-review.md`)

- Changes: [2026-11-18-single-agent-code-review/REQ-054](../2026-11-18-single-agent-code-review/spec.md#req-054-single-agent-skillmd-zero-repo-pollution-reporting-and-companion-rule-alignment), [2026-10-20-harness2-sandbox-and-inv-dom-review/REQ-047](../2026-10-20-harness2-sandbox-and-inv-dom-review/spec.md#req-047-ai-review-plugin-surface-validation-compliance)
- Source intent: User selection to convert all domain plugins—including `ai-review-plugin`—to `trigger: model_decision` (`0` always-on chars).
- Previous contract: `ai-review-plugin/rules/AGENTS.md` loads unconditionally (`1,707` always-on chars) on every turn.
- Statement: WHEN `ai-review-plugin` is enabled in Antigravity, THE plugin SHALL replace `rules/AGENTS.md` with `rules/ai-review.md` declaring YAML frontmatter `trigger: model_decision` and a non-empty `description:` covering `code-review`, `spec-review`, and `design-review`, preserving `<rule name="ai-review-governance">`, single-agent zero-repo-pollution `code-review`, sandboxed `spec-review`/`design-review`, `--dimension` (`inv`/`dom`), and all 3 skill triggers within `< 2500` chars so `surface_validator.py` reports `always_on_chars == 0`.
- AC-058-1 — Success: `rules/ai-review.md` exists (`< 2500` chars) with `trigger: model_decision` and non-empty `description:`, `rules/AGENTS.md` is absent, `surface_validator.py` returns `valid: true` with `always_on_chars == 0`, and all `ai-review-plugin` tests pass.
- AC-058-2 — Boundary/failure: IF `rules/ai-review.md` omits `description:` under `trigger: model_decision` or drops any of `spec-review`, `design-review`, or `code-review`, THEN `surface_validator.py` SHALL fail validation.

## Approvals and lifecycle history

- 2026-11-26 (`Planning -> In-Testing`): User approved full `0`-always-on conversion for `ai-review-plugin`, verified in [Run 1](./verification.md#run-1--2026-11-26).
