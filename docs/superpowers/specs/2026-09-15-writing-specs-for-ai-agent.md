# Writing specs for an AI development agent

## Overview

This guide provides a recommended boundary for `spec.md`, reusable agent instructions, a lightweight template, and examples. It is guidance, not a specification for an actual feature. No feature requirements or implementation choices have been approved.

**Key recommendation:** Treat a spec as a verifiable contract for intended behavior. Separate that contract from implementation design and execution tracking. Allow technical details when they are necessary contracts or established constraints.

**Next step:** Add your feature request, authoritative project references, and approval preferences to the reusable instructions below. Review the resulting draft before authorizing implementation.

## 1. Separate the questions: The 3-Document Feature Triad & Permanent Infrastructure

| Layer / Document | Lifecycle & Velocity | Question it answers | Typical contents |
| :--- | :--- | :--- | :--- |
| **Permanent Infrastructure Layer** (`AGENTS.md`, `rules/*.md`, `skills/`) | Standing, versioned with repository. Reusable across all features. | *"What tools, skills, security gates, and invariant reading order do I obey?"* | Tool permissions, sandbox rules, approval gates, review engines, invariant reading order. Never duplicated per feature. |
| **Feature Doc 1: `spec.md`** | **What does NOT change** (Agreed human contract). Stable baseline with controlled amendments. | *"What must be true, for whom, and why?"* | Scope, non-goals, normative requirements (`REQ-xxx`), acceptance criteria (`AC-xxx`), external contracts, domain rules. |
| **Feature Doc 2: `plan.md`** | **What changes on architectural discovery** (Technical blueprint). | *"How will we satisfy the spec?"* | Architecture, component mapping, internal data flow, migration approach, error handling, trade-offs, test strategy. |
| **Feature Doc 3: `tasks.md`** | **What changes continuously** (Dynamic workboard and execution state machine). | *"What work will be done, in what order?"* | Bounded tasks, dependencies (`Depends on: T-xxx`), requirement links (`Requirements: REQ-xxx`), verification proof. |
| **Optional Bookend: `research.md`** | Pre-flight discovery for complex brownfield codebases. | *"What are the existing facts and constraints?"* | Codebase survey, schema reverse-engineering, spike notes, dependency audits. |
| **Optional Bookend: `walkthrough.md`** | Post-flight delivery evidence and sign-off. | *"What was built and what automated proof passed?"* | Test execution output, before/after diff summary, screenshots, rollout sign-off. |

### The "Differential Rate of Change" Law
`plan.md` and `tasks.md` MUST remain separate documents:
- Design decisions and execution state mutate at fundamentally different cadences: what does not change vs. what changes on technical discovery vs. what changes continuously.
- Combining them causes continuous checkbox ticks (`- [ ]` -> `- [x]`) to rewrite and pollute the architectural blueprint.
- Keeping them separate prevents context churn and stops agents from mistaking an operational task for a product requirement.

### Document Authority Matrix
| Concern | Authoritative Location |
| :--- | :--- |
| Security gates, tool permissions, execution rules | Permanent Infrastructure (`AGENTS.md`) |
| Observable behavior, business rules, external contracts | `spec.md` |
| Technical architecture, data flow, component design | `plan.md` |
| Work queue, dependencies, verification evidence | `tasks.md` |

*Conflict Invariant*: Any conflict between documents triggers human escalation; never assume "the most recently read document wins."

### Full Requirement Traceability Graph
```text
spec.md (REQ-xxx) -> plan.md (Design for REQ-xxx) -> tasks.md (T-xxx -> REQ-xxx) -> code & tests
```

These filenames are a recommended convention, not a universal standard. For a small change, distinct sections in one file may be enough. For an existing repository, respect its established document structure.

Specs should be precise about outcomes and restrained about mechanisms. A compatible alternative implementation should satisfy the same spec unless an actual constraint rules it out.

## 2. What belongs in `spec.md`

1. **Problem and intended outcome.** Who needs the change, what is wrong today, and what improvement is intended. Distinguish supplied evidence from hypotheses.
2. **Actors and context.** Relevant users, external systems, roles, prerequisites, and important terminology. A user story is optional; testable behavior is not.
3. **Scope and non-goals.** What this change includes and deliberately excludes. Separate proposed ideas from committed requirements.
4. **Normative requirements.** Stable IDs such as `REQ-001`, one principal obligation per requirement, and observable expected behavior. Define any priority or normative vocabulary locally.
5. **Relevant scenarios.** Happy path, invalid input, permission denial, failure behavior, empty states, boundaries, retry/duplicate behavior, and concurrency where applicable. Do not add every possible scenario mechanically.
6. **Domain rules and external contracts.** Business invariants, relevant state transitions, inputs/outputs, validation, error semantics, compatibility promises, and side effects that consumers depend on.
7. **Established constraints.** Security, privacy, accessibility, retention, reliability, supported platforms, and performance requirements when applicable. Quantitative limits need a source or explicit approval, measurement conditions, and a verification method.
8. **Acceptance criteria.** Link criteria to requirement IDs. State preconditions, triggers, observable outcomes, and prohibited side effects. Include negative cases where relevant.
9. **Dependencies, assumptions, and questions.** Separate confirmed facts from assumptions and proposed decisions. Mark questions as blocking or non-blocking, identify who should decide if known, and explain the impact.
10. **Status and references.** Draft/review/approved status, approved revision where applicable, source references, and a short record of material contract changes. Never invent approval.

Product success metrics and acceptance criteria are different: adoption after launch may measure value, but it does not prove behavioral correctness. Include product metrics when useful without making up baselines, instrumentation, or targets.

### Technical details are not forbidden

Include a technical detail when changing it would break an agreed contract or a real constraint. For example:

- An externally consumed API field and its validation rules.
- A file format that must remain compatible.
- A required platform or approved technology constraint.
- An externally relevant consistency or idempotency guarantee.

Prefer a reference to the canonical schema or contract instead of copying it. Internal function names, component decomposition, indexing choices, and algorithm selection generally belong in the plan unless explicitly constrained.

## 3. What must not appear as committed spec content

| Avoid | Why / where it belongs |
| --- | --- |
| Coding sequence, file-by-file edits, shell commands, task checkboxes | Execution mechanics belong in `plan.md` or `tasks.md`. Acceptance checklists are still appropriate in the spec. |
| Arbitrary framework, database, library, or class choices | Design decisions belong in the plan; genuine constraints remain in the spec. |
| Production implementation code | Keep the contract readable. Small illustrative inputs/outputs or normative schemas are appropriate when they define behavior. |
| Vague obligations such as “fast,” “secure,” or “user-friendly” | Replace with verifiable behavior, or flag the missing decision. Do not manufacture precision. |
| Invented users, research, repository facts, targets, dependencies, or approvals | Cite available sources and label uncertainties explicitly. |
| Silent scope expansion, “while we are here” work, speculative future features | Record exclusions or separately labeled proposals; do not authorize implementation implicitly. |
| Contradictory or duplicated sources of truth | Link canonical contracts; surface conflicts for resolution. |
| Debugging transcripts, command outputs, progress diaries, completed-work claims | Keep these in execution/review records, not the behavior contract. |
| Secrets, credentials, real customer records, unnecessary personal information | Use synthetic examples and safe references. |
| Instructions to bypass project rules or weaken acceptance criteria to fit the code | Agent governance belongs in its instructions; discrepancies require explicit review. |

Avoid boilerplate that contributes no decision or verification value. Empty sections do not make a spec complete.

## 4. Standing Agent Infrastructure (AGENTS.md & Permanent Rules)

Place these reusable governance instructions directly into your permanent `AGENTS.md` or repository rules—never create a 4th per-feature markdown file for them (prevents instruction drift):

```text
You are drafting a feature specification for spec-driven development.

INPUTS
- Feature request: [insert request]
- Authoritative references: [insert documents or repository paths]
- Existing workflow/conventions: [insert if known]

OBJECTIVE
Create spec.md as a concise, verifiable contract for intended behavior.
Do not implement the feature or produce an implementation plan yet.
Use the repository's established spec location and format if one exists.

PROCESS
1. Read the supplied request and relevant available project references.
   For an existing system, inspect only the relevant contracts and code
   needed to understand current behavior. Do not claim inspection you
   did not perform. If access is unavailable, state that limitation.
2. Distinguish current behavior from desired behavior. Do not assume
   existing code is correct or that it overrides the requested change.
   Surface conflicts between authoritative inputs instead of guessing.
3. Identify the problem, actors, intended outcome, in-scope behavior,
   non-goals, existing constraints, and relevant dependencies.
4. Separate confirmed requirements, proposals, assumptions, and questions.
   Ask targeted questions when answers would materially change behavior,
   scope, permissions, data handling, compatibility, or verification.
   If answers are unavailable, produce a clearly marked partial draft;
   mark affected areas blocked rather than inventing their contracts.
5. Write atomic normative requirements with stable IDs such as REQ-001.
   Define MUST as required for this change and MUST NOT as prohibited.
   Keep unapproved optional ideas outside committed requirements.
6. For every normative requirement, provide linked acceptance criteria.
   Use Given/When/Then or an equally precise checklist. Include relevant
   preconditions, triggers, observable results, and prohibited side effects.
   Cover applicable success, failure, permission, and boundary scenarios.
7. Describe domain rules, interfaces, and technical constraints only as
   precisely as the agreed behavior requires. Reference canonical schemas
   rather than duplicating them. Leave unconstrained mechanisms to plan.md.
8. Consider privacy/security, accessibility, compatibility, data lifecycle,
   and reliability where relevant. Do not convert a checklist into new scope.
   Do not invent research, metrics, numeric limits, or technology mandates.
   For approved quantitative requirements, include measurement conditions
   and a verification method. Otherwise record the missing decision.
9. Self-review for ambiguity, contradictions, missing failure behavior,
   untestable requirements, missing acceptance coverage, and scope creep.
   Report unresolved blocking questions and impacted requirement IDs.
10. Leave the document in Draft status and request review. Do not claim
    approval, begin coding, or proceed to the plan without authorization.

RECOMMENDED SPEC SECTIONS
- Status and authoritative references
- Problem, actors, and intended outcome
- Scope and explicit non-goals
- Requirements with stable IDs
- Relevant behavior, domain rules, and external contracts
- Established constraints and non-functional requirements
- Acceptance criteria linked to requirement IDs
- Dependencies, assumptions, proposals, and open questions

EXCLUDE FROM SPEC.MD
- Step-by-step implementation instructions and coding task lists
- Unconstrained internal architecture, algorithms, or library choices
- Production implementation code and execution logs
- Unverified facts presented as facts, fabricated approval, and secrets
- Unapproved scope additions or unsupported future commitments

CHANGE CONTROL
After approval, propose changes to behavior, scope, constraints, or
acceptance criteria explicitly, with rationale and impact. Obtain approval
before changing the contract; then reconcile the plan, tasks, and tests.
Never weaken the spec merely to make an implementation or its tests pass.
Trace verification back to requirements, not just to existing code.

OUTPUT
Return the draft spec and a short summary of unresolved questions.
A draft may contain explicit TBDs; a build-ready contract must not depend
on unresolved blocking behavior or constraints. Do not invent answers
just to make the document look finished.
```

## 5. Lightweight `spec.md` template

Replace bracketed content with confirmed information; retain an explicit question where a decision is missing. Omit irrelevant optional sections.

```markdown
# [Feature name]

Status: Draft
Authoritative references: [links/paths, or explicitly unavailable]

## Problem and outcome
[Who needs the change, their problem, and the intended improvement.]

## Scope
In scope:
- [Committed capability]

Out of scope:
- [Explicit exclusion and brief reason]

## Actors and context
[Relevant actors, permissions, prerequisites, and terminology.]

## Requirements
MUST = required for this change. MUST NOT = prohibited.

### REQ-001 — [Single obligation]
[Actor/system] MUST [observable behavior] when [condition].
Source: [Reference or confirmed decision]

## Domain rules and external contracts
[Relevant validation, states, inputs/outputs, error semantics,
compatibility promises, and canonical contract references.]

## Constraints
[Established limits and obligations, with sources.
For quantitative constraints: threshold, measurement conditions,
and verification method. Unresolved decisions belong below.]

## Acceptance criteria
### AC-001 — verifies REQ-001
- Given [precondition]
- When [trigger]
- Then [observable result]
- And [important side effect or prohibited side effect]

[Add relevant negative and boundary scenarios.]

## Dependencies and assumptions
[Confirmed dependencies, explicitly labeled assumptions, and impacts.]

## Open questions
- Q-001: [Decision needed]
  - Blocking: [Yes/no; affected requirements]
  - Decision owner: [If known]
  - Impact: [What cannot be specified or verified until resolved]
```

## 6. Example: replacing vagueness with a contract

Illustrative only; these behaviors are not requirements for your project.

**Too vague:** “Handle unauthorized edits securely.”

**Better requirement:** `REQ-007`: When a viewer attempts to change a document, the system MUST reject the change, preserve the stored document, and show a permission-denied result without exposing the restricted document contents.

**Acceptance criterion:** Given a viewer and an existing document, when the viewer submits a change, then the change is rejected, the document remains unchanged, and the result does not expose restricted contents.

**Plan detail, not spec detail:** “Implement an authorization middleware function and call it from the update handler.”

This requirement states a contract; the plan chooses the mechanism. Tests must verify the contract independently of whichever mechanism is chosen.

## 7. Final review gate

Before treating a draft as build-ready, ask:

- Can an engineer understand intended behavior without guessing material decisions?
- Can a tester determine pass/fail for every normative requirement?
- Are facts, desired changes, assumptions, and proposals distinguishable?
- Are scope exclusions and important prohibited side effects explicit?
- Are relevant contract and compatibility references authoritative and consistent?
- Are required quality constraints verifiable under stated conditions?
- Are all blocking questions resolved for the work being authorized?
- Has the responsible human actually approved this version and its scope?

A spec is detailed enough when it removes consequential ambiguity—not when it predicts every line of code.
