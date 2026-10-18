# Architectural Decision Records: Mechanical Spec-Gate & Traceability Enforcement

**Feature ID:** `2026-10-09-spec-gate-enforcement`  
**Governing Specification:** [`spec.md`](./spec.md)  
**Status:** Approved by Human Gate  

---

## ADR-031: Plugin Separation of Concerns (Inter-Plugin Division)

### Context
We need to enforce that specifications exist before code mutations occur. Two plugins are involved:
1. `antigravity-attention-guard-plugin`: Holds Antigravity lifecycle hooks (`PreToolUse`, `PostToolUse`, `Stop`) that intercept model actions, enforce delegation, and guard the context window.
2. `ai-review-plugin`: Owns the specification standard (`rules/spec-standard.md`), 5-Document Architecture templates, peer review engines, and specification verification logic.

We must decide where the mechanical interception and specification checking logic reside.

### Decision
- **`antigravity-attention-guard-plugin` acts as the Runtime Interceptor:** It registers the `PreToolUse` hook on `invoke_subagent` because it already controls agent lifecycle interception, tool authorization, and process governance.
- **`ai-review-plugin` acts as the Specification Authority & Verification Engine:** It implements `scripts/spec_checker.py`. This script contains the domain knowledge of what constitutes a valid `docs/specs/` hierarchy, parses `INDEX.md`, and validates document completeness.
- **Contract Boundary:** The hook in `attention-guard` executes or imports `spec_checker.py` from `ai-review-plugin` (or via standard CLI invocation with `--workspace`). If `ai-review-plugin` is not installed or the workspace lacks `docs/specs/`, `spec_checker.py` provides deterministic fallback rules.

### Consequences
- **Positive:** Clean separation between lifecycle interception mechanics (attention-guard) and specification domain logic (ai-review-plugin).
- **Positive:** `spec_checker.py` can be tested independently in `ai-review-plugin` using standard pytest suites without running the full Antigravity hook harness.
- **Trade-off:** Requires a cross-plugin runtime dependency: the hook must resolve the path to `spec_checker.py` via configuration or standard discovery paths.

---

## ADR-032: Exemption Policy for Subagent Lifecycles

### Context
Not all subagents perform workspace code mutations. Subagents are utilized for diverse tasks:
1. Read-only research (`TypeName == "research"`, `flash_lite` models, grep/file crawlers).
2. Domain translation pipelines in `agent-translator` (`translate`, `evaluate`, `refine`, `analyze`) that write strictly to isolated scratch directories under `runs/<book_slug>/`.
3. General-purpose implementation executors (`TypeName == "self"`, Role="Executor", or prompts instructing code modifications across workspace files).

If the spec gate indiscriminately blocked all subagents, research queries and book translations would grind to a halt whenever `docs/specs/` was not populated.

### Decision
We establish a strict, whitelist-based exemption policy:
- **Exempt Categories:**
  1. **Read-Only Research Subagents:** Identified by `TypeName == "research"` or roles explicitly declaring read-only investigation without file editing tools.
  2. **Domain Translation Pipeline:** Subagents with `TypeName` in `{"translate", "evaluate", "refine", "analyze"}` operating on book translation runs under `runs/`.
- **Gated Categories:**
  1. Subagents with `TypeName == "self"`.
  2. Subagents assigned roles containing keywords: `executor`, `developer`, `implementer`, `refactor`, `builder`, `patch`.
  3. Any subagent prompt containing instructions to create or edit workspace code files (`write_to_file`, `replace_file_content`, edit, modify, create).

### Consequences
- **Positive:** Zero friction for exploration, information retrieval, and dedicated external pipeline tasks.
- **Positive:** Total lockdown on unauthorized code mutation, preventing conversational drift.
- **Trade-off:** Requires accurate heuristic classification of subagent prompts and roles; malicious or subtle prompt circumvention must be monitored.

---

## ADR-033: Deterministic AST-based CLI Traceability

### Context
To ensure continuous adherence to specifications, we must prevent "specification rot"—where developers or agents add CLI flags, parameters, or endpoints that have no corresponding requirement in `docs/specs/`.
We considered three approaches to verify traceability:
1. **Dynamic Reflection / Help Parsing:** Running scripts with `--help` and scraping text output.
2. **Regex Scanning:** Using regular expressions across Python source files to find flags like `--\w+`.
3. **Static Abstract Syntax Tree (AST) Analysis:** Parsing Python syntax trees via the standard library `ast` module.

### Decision
We adopt **Static AST Analysis** via `ast.parse()` in `tests/test_spec_traceability.py`:
- Static AST inspection visits all `Call` nodes matching `*.add_argument(...)`.
- It reliably extracts positional and keyword arguments (e.g. `"-p"`, `"--prior-review"`, `"--workspace"`) without executing untrusted code or suffering from shell subprocess overhead.
- AST parsing handles multiline calls, comments, and complex argument lists without regex fragility.
- The test extracts requirement IDs (`REQ-\d+`) from `docs/specs/**/*.md` and enforces that every discovered CLI flag appears in the normative specification text of an active or approved spec.

### Consequences
- **Positive:** 100% deterministic, zero test side effects, millisecond execution time.
- **Positive:** Cannot be broken by help text formatting changes or missing runtime dependencies.
- **Trade-off:** Static AST traversal requires handling variations in how `argparse` is called (e.g., helper wrapper functions vs direct calls).

---

## ADR-034: Fast-Path Disambiguation (Rigid Boundary Quantification)

### Context
Conversational drift frequently occurs because rules state that "small bug fixes, typos, and configuration tweaks" can bypass Phase 1 specifications without defining what "small" means. Agents rationalize adding multiple features, new files, and CLI flags under the guise of "addressing the prompt directly".

### Decision
We eliminate subjective adjectives ("small", "trivial", "quick") and establish **rigid mathematical criteria** for Fast-Path eligibility:
- **Fast Path Permitted ONLY IF:**
  1. The change affects `<= 1` non-test code file.
  2. Total lines changed `<= 50` lines.
  3. Zero new CLI options, flags, or configuration keys are introduced.
  4. Zero data contracts (`schemas/*.json`, database migrations) are modified.
  5. The change is a bug fix, typo correction, or localized formatting fix.
- **Mandatory 5-Document Specification Required IF:**
  1. `>= 2` non-test code files are created or modified.
  2. Any CLI argument or command flag is added or modified.
  3. Any JSON schema or public interface is altered.
  4. Any negative prompt constraint (e.g., *"do not compile"*, *"leave tests for later"*) is detected—negative constraints are defined as execution parameters, NEVER as spec exemptions.

### Consequences
- **Positive:** Unambiguous heuristic: if an agent touches 2 files or adds a CLI flag, Phase 1 spec is mathematically required.
- **Positive:** Eliminates conversational momentum rationalizations.
- **Trade-off:** Even small multi-file refactors require scaffolding `spec.md`, `decisions.md`, and `design.md`, which adds deliberate friction to ensure architectural integrity.
