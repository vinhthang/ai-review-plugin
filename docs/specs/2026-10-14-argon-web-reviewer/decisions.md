# Architectural Decision Records: Argon Web Reviewer & Pluggable Engine Architecture

**Feature ID:** `2026-10-14-argon-web-reviewer`  
**Governing Specification:** [`spec.md`](./spec.md)  
**Status:** In Review (Disambiguated via `/grill-me`)  

---

## ADR-036: First-Class Review Engine Integration (`--engine argon-web`)

### Context
We need to introduce a Gemini web reviewer running via Microsoft Edge AppleScript. We had options:
1. Pure standalone CLI script (`review_edge_applescript.py`) writing arbitrary markdown reviews to disk.
2. First-class review engine adapter integrated into `scripts/peer_review.py` returning canonical `ReviewEnvelope` structured JSON (`review.json`) for automated gating.
3. Hybrid dual-mode CLI and engine.

### Decision
During `/grill-me` disambiguation, the decision was made to integrate Argon Web Reviewer **strictly into `scripts/peer_review.py` as an engine adapter (`--engine argon-web`) returning structured JSON (`review.json`) for automated gating**, while retaining the standalone runner script for direct CLI invocations.

### Consequences
- **Positive:** Fits cleanly into Dalio review FSM, enabling automated P0/P1 issue gating in `spec-review` and `design-review` skills.
- **Positive:** Single unified CLI facade (`peer_review.py --engine argon-web`).
- **Trade-off:** Requires parsing and validating the web LLM's response into the canonical schema.

---

## ADR-037: Pluggable Engine Registry Architecture

### Context
Currently, `scripts/review/audit.py` hardcodes engine choices (`choices=["workbuddy", "codex"]`) and uses manual `if/elif` branches for instantiation and binary checks. Adding `argon-web` would worsen coupling if added as another `elif`.

### Decision
Implement a **Pluggable Engine Registry** pattern in `scripts/review/engines/`:
- `scripts/review/engines/__init__.py` maintains `ENGINE_REGISTRY: Dict[str, Type[ReviewEngineAdapter]]`.
- Adapters define metadata and methods: `name`, `supported_prefixes`, and `ReviewEngineAdapter` contract.
- `audit.py` retrieves dynamic engine choices from `get_registered_engines()` and instantiates adapters via `get_engine_adapter(name)`.
- Removes all hardcoded `if engine_name == ...` checks from `scripts/review/audit.py`.

### Consequences
- **Positive:** Open/Closed Principle: Future review engines can be registered without modifying `audit.py`.
- **Positive:** Cleaner modular architecture and easier testing.

---

## ADR-038: Hybrid JSON + Markdown Review Envelope Extraction

### Context
Unlike headless CLIs (`cbc`, `codex`) that output strict JSON schemas via native flags, Gemini on `gemini.google.com` may return:
- Raw JSON.
- Markdown code blocks containing JSON (````json ... ````).
- Conversational markdown with severity tags (e.g. `[Critical/Blocker]`, `[Warning]`, `[Suggestion]`).

### Decision
Adopt a **Hybrid JSON + Markdown Parser**:
1. Prompt Gemini in Edge with structured JSON instructions adhering to `schema.json`.
2. Upon receiving the response:
   - Check if response contains valid JSON or fenced JSON block: extract and validate directly.
   - If JSON decoding fails, execute a regex-based markdown issue extractor mapping:
     - `[Critical/Blocker]` / `[Critical]` / `[Blocker]` -> `P0` or `P1`.
     - `[Warning]` -> `P1` or `P2`.
     - `[Suggestion]` -> `P2`.
   - Wrap extracted issues into canonical `ReviewEnvelope`.

### Consequences
- **Positive:** Resilient against LLM non-determinism in the web chat interface.
- **Positive:** Prevents pipeline aborts due to minor conversational wrappers.

---

## ADR-039: In-Repo Native Implementation (Zero External Runtime Dependency)

### Context
An external script existed at `/Users/thanghoang/.gemini/antigravity/scratch/gemini_review_agent/review_edge_applescript.py`. We need to determine how our production plugin relates to it: whether to reference that path or implement it natively.

### Decision
The scratch script is used **strictly as an architectural and behavioral reference, not referenced or imported at runtime**.
The runner is implemented 100% self-contained in `scripts/review/runners/edge_applescript_runner.py` within `ai-review-plugin`.
No code, configuration, or adapter in `ai-review-plugin` will ever point to or depend on the scratch file path.

The native runner will serve a dual purpose:
1. Executable standalone CLI script for arbitrary markdown review:
   `python3 scripts/review/runners/edge_applescript_runner.py <files...> --out design_review.md`
2. Subprocess executable launched by `ArgonWebAdapter.build_command(...)`.

### Consequences
- **Positive:** 100% self-contained repository with zero coupling to local scratch paths.
- **Positive:** Fully version-controlled, portable, and reproducible across environments.
- **Positive:** Scratch files can be deleted without impacting `ai-review-plugin`.

---

## ADR-041: Reviewer Hardening & Bijective Parsing (Feedback from Live Architectural Review)

### Context
During the live review round against the project's architecture documents, the Gemini Argon reviewer identified four critical/warning risks:
1. False-"Approved" Gate Risk in Markdown Fallback if responses are unformatted or refusal/error banners.
2. Stale DOM Extraction Race Condition when reusing existing Gemini conversation tabs.
3. Non-deterministic severity mapping in `[Warning]`.
4. Multi-block code fence extraction selecting illustrative JSON in target documents instead of the reviewer's output.

### Decision
1. **Bijective Severity Mapping**:
   - `[Critical]`, `[Blocker]`, `[Critical/Blocker]` $\rightarrow$ `P0`
   - `[Warning]` $\rightarrow$ `P1`
   - `[Suggestion]` $\rightarrow$ `P2`
2. **Fail-Closed Fallback**: The parser aborts with code 2 if neither valid JSON nor recognized severity tags exist, forbidding empty issue lists unless an explicit positive confirmation sentinel (`status: approved`, `all checks passed`) is matched and zero refusal/error substrings are present.
3. **Reverse Code Fence Search**: Reverse-iterates over fenced JSON blocks, verifying schema conformance (`isinstance(data, dict)` with an `issues` list) to avoid picking up target document examples.
4. **Pre-Send DOM Baseline Count**: Records message container count before clicking Send, blocking until `count > initial_count` before entering completion stability polling.

### Consequences
- **Positive**: Eliminates false approvals and stale DOM extractions.
- **Positive**: Strict bijective mapping ensures predictable gate outcomes.
