# Design Blueprint: Mechanical Spec-Gate & Traceability Enforcement

**Feature ID:** `2026-10-09-spec-gate-enforcement`  
**Governing Specification:** [`spec.md`](./spec.md)  
**Status:** Approved by Human Gate  

---

## 1. System Topology & Inter-Plugin Communication

The architecture spans two distinct plugins connected via runtime hook dispatch and shared filesystem contracts:

```
┌─────────────────────────────────────────────────────────────┐
│             Antigravity Agent Runtime (IDE / CLI)            │
└──────────────────────────────┬──────────────────────────────┘
                               │ Invokes Tool: invoke_subagent
                               ▼
┌─────────────────────────────────────────────────────────────┐
│          antigravity-attention-guard-plugin (Hooks)         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ PreToolUse Hook: scripts/spec-gate.py                 │  │
│  │ 1. Parse PreToolUse JSON payload                      │  │
│  │ 2. Evaluate Subagent Exemption Heuristic              │  │
│  │ 3. If Gated: Execute / Call spec_checker.py           │  │
│  └───────────────────────────┬───────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────┘
                               │ Runs subprocess or imports
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 ai-review-plugin (Domain Logic)             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Verification Engine: scripts/spec_checker.py          │  │
│  │ - Inspects <workspace>/docs/specs/INDEX.md            │  │
│  │ - Inspects <workspace>/docs/specs/<active-id>/        │  │
│  │ - Verifies spec.md, decisions.md, design.md           │  │
│  │ - Returns: {"valid": bool, "active_id": str, ...}     │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ CI Fitness Function: tests/test_spec_traceability.py  │  │
│  │ - AST traversal of scripts/*.py (add_argument)        │  │
│  │ - Maps flags -> REQ-xxx in docs/specs/**/*.md         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Data Contracts & Hook Payload Schema

### 2.1 Antigravity `PreToolUse` Hook Input Payload
When Antigravity invokes a tool, `PreToolUse` passes a JSON payload via standard input to the configured hook script:

```json
{
  "conversationId": "ddea9846-e309-455d-9f18-9b7e0d7d35d3",
  "stepIdx": 42,
  "transcriptPath": "/Users/thanghoang/.gemini/antigravity/brain/ddea9846-e309-455d-9f18-9b7e0d7d35d3/.system_generated/logs/transcript.jsonl",
  "artifactDirectoryPath": "/Users/thanghoang/.gemini/antigravity/brain/ddea9846-e309-455d-9f18-9b7e0d7d35d3",
  "toolCall": {
    "name": "invoke_subagent",
    "args": {
      "Subagents": [
        {
          "TypeName": "self",
          "Role": "Feature Implementer",
          "Prompt": "Implement TOC generator in scripts/toc_builder.py and add --with-toc flag.",
          "Model": "flash"
        }
      ]
    }
  }
}
```

### 2.2 Hook Decision Output Schema
The hook script writes a JSON decision object to standard output:
- **Allow:**
  ```json
  {
    "decision": "allow"
  }
  ```
- **Deny:**
  ```json
  {
    "decision": "deny",
    "reason": "Specification Gate Violation: No active specification found under docs/specs/. Feature implementations modifying code or adding CLI flags require Phase 1 specification (spec.md, decisions.md, design.md) registered in docs/specs/INDEX.md with status 'Planning' or 'In-Progress'."
  }
  ```

---

## 3. Subagent Classification Heuristics

The `spec-gate` hook analyzes each subagent in the `Subagents` array to categorize it as **Exempt** or **Gated**:

```python
EXEMPT_TYPE_NAMES = {"research", "translate", "evaluate", "refine", "analyze"}
MUTATING_ROLE_KEYWORDS = {
    "executor", "developer", "implementer", "refactor",
    "builder", "patch", "coder", "scaffolder"
}
CODE_MUTATION_TRIGGERS = [
    r"\b(write_to_file|replace_file_content)\b",
    r"\b(create|modify|edit|update|delete|refactor|implement)\b.*\b(\.py|\.ts|\.js|\.rs|\.go|\.java|\.json|\.sh)\b",
    r"\badd\b.*\b(flag|argument|option|endpoint|cli)\b"
]
```

### Classification Algorithm:
1. **Type Exemption:** If `subagent.get("TypeName") in EXEMPT_TYPE_NAMES` and `TypeName != "self"`:
   - Mark as **Exempt**.
2. **Model Exemption:** If `subagent.get("Model") == "flash_lite"` and no code mutation trigger matches prompt:
   - Mark as **Exempt**.
3. **Explicit Gating:** If `subagent.get("TypeName") == "self"` OR any keyword in `MUTATING_ROLE_KEYWORDS` matches `subagent.get("Role", "").lower()`:
   - Mark as **Gated**.
4. **Prompt Heuristic:** If regex search for `CODE_MUTATION_TRIGGERS` matches `subagent.get("Prompt", "")`:
   - Mark as **Gated**.
5. **Default:** Subagents not meeting exemptions are treated as **Gated** (Fail-Closed).

---

## 4. `scripts/spec_checker.py` Architecture

The spec checker serves as a self-contained, standalone verification engine.

### 4.1 Core Functions
```python
def parse_specs_index(index_path: str) -> list[dict]:
    """Parses docs/specs/INDEX.md markdown table into structured records.
    Returns: [{'feature_id': str, 'title': str, 'status': str, 'req_range': str, 'spec_path': str}]
    """

def get_active_specifications(records: list[dict]) -> list[dict]:
    """Filters records for status in {'Draft', 'Planning', 'In-Progress', 'Approved'}."""

def validate_spec_package(package_dir: str) -> tuple[bool, list[str]]:
    """Checks for existence of spec.md, decisions.md, and design.md.
    Validates that spec.md contains at least one REQ-xxx identifier.
    Returns: (is_valid, list_of_missing_or_invalid_items)
    """

def verify_active_specification(workspace_root: str) -> dict:
    """Master entrypoint.
    Returns:
    {
        "status": "valid" | "no_active_spec" | "incomplete_package" | "no_index",
        "active_feature_id": str | None,
        "missing_files": list[str],
        "errors": list[str]
    }
    """
```

### 4.2 CLI Interface and Exit Codes
```bash
python3 scripts/spec_checker.py --workspace <path> [--json]
```
- Exit Code `0`: Active, fully valid specification package found.
- Exit Code `1`: No active specification found, or package is missing required files (`spec.md`, `decisions.md`, `design.md`).
- Exit Code `2`: `docs/specs/INDEX.md` is missing, unparseable, or filesystem error.

---

## 5. AST Visitor & Traceability Engine

Implemented in `tests/test_spec_traceability.py`, the traceability engine validates that no CLI flags are introduced without specification backing.

### 5.1 AST Visitor
```python
import ast

class CLIArgumentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.cli_flags = []  # list of tuples: (flag_name, line_no, filename)

    def visit_Call(self, node):
        # Look for *.add_argument(...)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith("-"):
                        self.cli_flags.append(arg.value)
        self.generic_visit(node)
```

### 5.2 Requirement Extraction & Traceability Mapping
1. `extract_cli_arguments(scripts_dir)`: Runs `CLIArgumentVisitor` over all `*.py` files in `scripts/`.
2. `extract_spec_requirements(specs_dir)`:
   - Scans all `docs/specs/**/spec.md`.
   - Extracts all requirement sections (`### REQ-\d+:`).
   - Maps each `REQ-xxx` to textual mentions of flags (`--[a-z0-9-]+`).
3. `assert_all_flags_traced(flags, spec_mappings)`:
   - Asserts `flag in spec_mappings` for all discovered CLI flags.
   - Outputs detailed report of any orphaned flags.

---

## 6. Failure Modes & Security Threats

| Failure Mode / Threat | Threat Description | Mitigation |
| :--- | :--- | :--- |
| **Renamed Subagent Role** | Agent sets `Role="Doc Writer"` but prompt instructs mutating Python scripts. | Keyword matching on prompt (`CODE_MUTATION_TRIGGERS`) and `TypeName=="self"` gate regardless of role string. |
| **Malformed Tool Args** | Agent passes `Subagents` as string or malformed dictionary to bypass hook. | Hook parses defensively with try/except; invalid JSON or missing `Subagents` array triggers fail-closed `decision: deny`. |
| **Multi-Workspace Path Drift** | Agent executes against secondary workspace where `docs/specs/` is not in CWD. | Spec checker resolves workspace root from Antigravity environment (`AGY_ACTIVE_WORKSPACE` or tool call `Cwd`). |
| **Symlink Traversal** | Spec package points to symlink outside repository to bypass requirements. | `validate_spec_package` resolves `os.path.realpath` and validates containment within workspace. |
| **Ghost Requirement IDs** | Developer invents `REQ-999` in code comments without adding to `spec.md`. | Traceability engine extracts requirement IDs strictly from authoritative `docs/specs/**/spec.md` files. |
