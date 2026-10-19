# Architecture Decision Records (ADR): Codebase Simplification, Deduplication & Modularization

- **Feature ID**: `2026-10-19-simplification-and-deduplication`
- **Status**: `Planning`

## `ADR-021`: Single-Source `rules/spec-standard.md` Ownership in `spec-driven-plugin`
- **Context**: Both `ai-review-plugin` and `spec-driven-plugin` shipped `rules/spec-standard.md`, causing the agent runtime to load duplicate `<rule name="spec-standard">` blocks into the prompt context on every turn and allowing the two copies to drift out of sync.
- **Decision**: Remove `ai-review-plugin/rules/spec-standard.md` so `spec-driven-plugin/rules/spec-standard.md` is the single authoritative specification rule. Synchronize `scripts/spec_checker.py` with standard `parser.add_argument` declarations and update `scripts/review/governance.py` to split table cells on unescaped pipes (`r"(?<!\\)\|"`).
- **Consequences**: Eliminates duplicate system prompt rules and prevents escaped-pipe table corruption in `governance.py`.
- **Addresses**: `REQ-041`

## `ADR-022`: Decompose `audit.py` and `edge_applescript_runner.py` Below the 500-Line AST Threshold
- **Context**: `scripts/review/audit.py` (509 lines) and `scripts/review/runners/edge_applescript_runner.py` (536 lines) exceeded the 500-line `ast-gate.py` threshold, blocking direct file inspection and burying orchestration logic inside a 412-line `_main()` function.
- **Decision**:
  1. Extract prompt construction into `scripts/review/prompts.py` (`build_review_prompt()`) and extract sandbox preparation (`prepare_repo_sandbox()`) and subprocess execution (`execute_engine_process()`) helpers in `scripts/review/audit.py`.
  2. Extract `CDPClient` into `scripts/review/runners/cdp_client.py` and re-export it from `edge_applescript_runner.py` for backward compatibility.
- **Consequences**: Brings every Python file in `ai-review-plugin` well under 450 lines while preserving all existing imports and CLI behavior.
- **Addresses**: `REQ-042`, `REQ-043`

## `ADR-023`: Centralize Issue Description Extraction in `scripts/review/models.py`
- **Context**: Both `scripts/review/audit.py` and `scripts/review/engines/argon.py` duplicated fallback key lookups (`details`, `message`, `summary`, `finding`, `title`, `comment`, `text`, `note`, etc.) when normalizing issue dictionaries.
- **Decision**: Define `extract_issue_description(item: Dict[str, Any]) -> str` in `scripts/review/models.py` and call it from both `audit.py` and `argon.py`.
- **Consequences**: Removes duplicated normalization loops and ensures consistent issue description extraction across all engines.
- **Addresses**: `REQ-044`
