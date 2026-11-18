# Architectural Decision Records: Feature-Scoped Document Architecture & Versioned Reviews

## ADR-011: Feature-Scoped Package Layout & Central `INDEX.md` Registry (`REQ-001`, `REQ-002`)
- **Status**: Accepted
- **Context**: Flat specification files and single-file `review.json` outputs overwrote historical review rounds and lacked a central discovery index.
- **Decision**: Organize specifications under `docs/specs/<feature-id>/` registered in `docs/specs/INDEX.md`.

## ADR-012: Stateless `--prior-review` Context Injection & Recursive Discovery (`REQ-003`, `REQ-004`)
- **Status**: Accepted
- **Context**: Iterative review rounds require verifying resolution of prior P0/P1 defects without introducing stateful locks in `peer_review.py`.
- **Decision**: Pass prior review JSON via `--prior-review <path>` sanitized and bounded to 2,500 chars inside `<prior_review_context>` tags, and support recursive spec discovery across `docs/specs/**`.
