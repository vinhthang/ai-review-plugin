# Technical Design: Sandbox Verdict Anti-Leak, Orthogonal INV/DOM Review & Surface Compliance

- **Feature ID**: `2026-10-20-harness2-sandbox-and-inv-dom-review`
- **Spec**: [spec.md](spec.md)
- **Decisions**: [decisions.md](decisions.md)

---

## 1. Component & Interface Design

### 1.1 `scripts/review/audit.py` (Addresses: `REQ-045`, `REQ-046`)
- Define `VERDICT_LEAK_FILES = ("review.md", "SELF_REVIEW.md", "REVERIFICATION_REPORT.md", "architecture_review.md", "traceability_audit.json")`.
- Add `--exclude=<name>` for each entry in `VERDICT_LEAK_FILES` in `prepare_repo_sandbox()`, include them in the `shutil.copytree` ignore set, and call `assert_no_verdict_leaks(repo_copy)` (which scans `repo_copy` and raises `ValueError` if any file in `VERDICT_LEAK_FILES` exists, unless it is the explicit target being reviewed).
- Add `--dimension` (`choices=["all", "inv", "dom"]`, `default="all"`) to `_main()` argument parser and pass `dimension=args.dimension` to `build_review_prompt()`.

### 1.2 `scripts/review/prompts.py` (Addresses: `REQ-046`)
- Add `dimension: str = "all"` parameter to `build_review_prompt()` (keeping file strictly `< 500` lines).
- When `dimension == "inv"`, append the Harness² Invariant dimension lens (`Dimension Lens (INV — Mechanical & Runtime Invariants): Focus strictly on process safety, CLI argument boundaries, error handling, resource cleanup, deterministic execution, and test falsifiability. Do not flag domain prose or subject-matter style.`).
- When `dimension == "dom"`, append the Harness² Domain dimension lens (`Dimension Lens (DOM — Domain & Specification Semantics): Focus strictly on requirement completeness (REQ-xxx/AC-xxx), state machine transitions, data contracts, consistency relationships, and domain invariants.`).

### 1.3 `rules/AGENTS.md` & Skill Deduplication (Addresses: `REQ-047`)
- Create `rules/AGENTS.md` in `ai-review-plugin` defining `<rule name="ai-review-governance">` with explicit skill triggers for `spec-review`, `design-review`, and `code-review`.
- Remove duplicate `skills/en-vi-book-translation-review/` from `ai-review-plugin` (and `~/.gemini/config/skills/en-vi-book-translation-review/`).
