# Architecture Decision Records: Alibaba Open-Code-Review Language Rule Corpus & Glob Matcher Integration

- **Feature ID**: `2026-10-30-ocr-language-rules-integration`
- **Date**: `2026-10-30`

---

## `ADR-010`: Vendor `alibaba/open-code-review` Rule Corpus & Implement Native Python Matcher Over External `ocr` CLI Dependency
- **Status**: Accepted
- **Addresses**: `REQ-048`, `REQ-049`
- **Context**:
  `alibaba/open-code-review` provides 57 high-precision language review checklists (`internal/config/rules/rule_docs/*.md`) and a deterministic glob/sniff router (`system_rules.json`, `system_rules.go`, `sniffer.go`). We need to decide whether to invoke the external `ocr delegate rule` Go/npm CLI binary at runtime or vendor the static rule files and port the ~120-line matcher directly into Python (`scripts/review/rule_matcher.py`).
- **Decision**:
  Vendor `system_rules.json` and `rule_docs/*.md` (Apache-2.0) into `scripts/review/rules/` and implement the glob/brace/sniff matcher natively in Python (`scripts/review/rule_matcher.py`) with zero external binary or third-party pip dependencies.
- **Trade-offs & Risks**:
  - *Pros*: Zero subprocess overhead, zero npm/`ocr` binary installation requirement, offline deterministic execution, and no risk of `ocr`'s default file filter silently excluding `*_test.go` or `tests/**` files in violation of `RULE[tdd.md]`.
  - *Cons*: Upstream updates to `alibaba/open-code-review`'s `rule_docs/*.md` require periodic sync into `scripts/review/rules/`.
- **Rejected Alternatives**:
  - *Shelling out to `ocr delegate rule --format json`*: Rejected because it requires global npm installation (`@alibaba-group/open-code-review`), adds subprocess latency, and couples `ai-review-plugin` to an external binary lifecycle.
  - *Creating a separate standalone `open-code-review` Antigravity plugin*: Rejected because it collides with `ai-review-plugin`'s `code-review` skill triggers and violates `attention-guard` context isolation in delegation mode.

---

## `ADR-011`: Inject Deduplicated `<language_review_rules>` and Ground A/B Self-Verification Guardrails Strictly in `--mode code`
- **Status**: Accepted
- **Addresses**: `REQ-050`
- **Context**:
  `scripts/review/prompts.py` constructs prompts for three modes (`spec`, `design`, `code`). In `--mode code`, injecting language-specific rules for every file without deduplication or size bounds could bloat prompts on large diffs, and LLM reviewers frequently hallucinate comments on unchanged lines or misread diff context.
- **Decision**:
  In `build_review_prompt(..., mode="code")`, extract modified paths from `target_content` (`+++ b/<path>`), resolve and deduplicate matching rules via `rule_matcher.py` within a `60,000`-character ceiling, and append both `<language_review_rules>` and the Ground A / Ground B verification guardrail (derived from `alibaba/open-code-review`'s `review_filter_task_user.md`). Keep `spec` and `design` modes untouched.
- **Trade-offs & Risks**:
  - *Pros*: Gives single-pass review engines (`deepseek-v4.1-flash`, `argon`, `codex`) both language-specific defect checklists and strict Ground A/B self-filtering in one pass without extra LLM round-trips.
  - *Cons*: Increases `--mode code` prompt size by ~3 KB–18 KB depending on the number of distinct languages in the diff.
- **Rejected Alternatives**:
  - *Running a separate second LLM pass for `REVIEW_FILTER_TASK`*: Rejected because `WorkBuddyAdapter` and `ArgonWebAdapter` have high per-invocation startup latency (~15–45s); embedding Ground A/B self-verification + negative language guardrails directly in the audit prompt achieves false-positive suppression with zero extra round-trip latency.
