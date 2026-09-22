# Design: Feature-Scoped Document Architecture & Versioned Reviews

## Architectural Blueprint
This design realizes REQ-011 through REQ-020 by implementing stateless prior-review injection and recursive discovery.

### 1. Stateless Prior Review Protocol
- `peer_review.py` accepts `--prior-review <path>`.
- `sanitize_prior_review()` sanitizes control characters, escapes `</prior_review_context>` to `&lt;/prior_review_context&gt;`, and bounds to 2,500 characters with `... [truncated]`.
- Enforces relative path containment to prevent directory traversal outside repository root.
- Reverts to standard exit codes (1 on blocking issues, 0 on clean, 2 on CLI runtime error).

### 2. Recursive Review Discovery
- `spec-review` skill searches `docs/superpowers/specs/**/spec.md` and `docs/superpowers/specs/*.md`.
- `design-review` skill searches `docs/superpowers/specs/**/design.md` and `docs/superpowers/specs/*.md`.
