# Document Architecture for AI Agents (The 5-File Model)

This guide defines the 5-File Architecture for agentic engineering, superseding the earlier 3-File Triad.

## 1. The Five Documents
- **`spec.md`**: What must be true. Authority on behavior.
- **`decisions.md`**: What was decided. Constrains the solution space. Append-only.
- **`design.md`**: How we build it. Must satisfy spec and decisions.
- **`tasks.md`**: What remains. Derived and volatile.
- **`verification.md`**: Evidence it works. Append-only per test run.

## 2. Precedence Order
When documents disagree:
1. `spec.md` wins over everything.
2. `decisions.md` wins over design.
3. `design.md` wins over tasks.
4. `verification.md` invalidates but never redefines.

**Conflict Protocol**: Stop work. State the conflict. Apply precedence. Never silently reconcile.

## 3. Requirement IDs (The Spine)
Normative requirements get a stable ID (e.g., REQ-007). This ID must be cited in decisions, design, tasks, and verification.

## 4. Scaling (Opt-In Switches)
The base set is 3 files: `spec.md` + `design.md` + `tasks.md`.
- **Switch A (`decisions.md`)**: Add when rationale must outlive the decision.
- **Switch B (`verification.md`)**: Add when correctness must be proven (e.g., audit trails, data migrations).
