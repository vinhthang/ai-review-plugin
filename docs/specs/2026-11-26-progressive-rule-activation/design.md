# Design: Progressive `model_decision` Activation for `ai-review-plugin` Rules

Governing specification: [spec.md](./spec.md)

## Components

- `rules/ai-review.md` (`[NEW]`): Frontmatter `trigger: model_decision` + `description:` covering `code-review`, `spec-review`, and `design-review`; body retains `<rule name="ai-review-governance">`, single-agent zero-repo-pollution `code-review`, sandboxed `peer_review.py` with `assert_no_verdict_leaks`, `--dimension` (`inv`/`dom`), and all 3 skill triggers (`< 2500` chars) (REQ-058 / AC-058-1).
- `rules/AGENTS.md` (`[DELETE]`): Removed so Antigravity does not inline the rule unconditionally (REQ-058 / AC-058-1).
- `tests/test_harness2_review.py` & `tests/test_prepare_code_review.py` (`[MODIFY]`): Assert `rules/ai-review.md`, `trigger: model_decision`, absence of `rules/AGENTS.md`, `< 2500` chars, and `always_on_chars == 0`.

## Boundaries and recovery

- If `rules/ai-review.md` lacks `description:` or omits any of the 3 skill names, `surface_validator.py` rejects the bundle before commit (REQ-058 / AC-058-2).
