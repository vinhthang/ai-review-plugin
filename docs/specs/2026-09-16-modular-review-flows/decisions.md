# Architectural Decision Records: Modular Review Architecture Refactor

## ADR-021: 3-Stage Semantic Lifecycle Decomposition (`REQ-021`, `REQ-022`)
- **Status**: Accepted
- **Context**: The legacy 13-state review loop caused state explosion and conflicted with the root-cause escalation state machine.
- **Decision**: Decompose review workflows into three semantic stages: **Audit**, **Remediation**, and **Governance**, bounded by `escalation_counter < 3`.

## ADR-022: Stateless Technical Rebuttal & Versioned Archival (`REQ-023`, `REQ-024`, `REQ-025`)
- **Status**: Accepted
- **Context**: Dedicated debate subagents diluted context and overwrote prior `review.json` artifacts.
- **Decision**: Inject technical rebuttals via stateless `--prior-review` and archive review rounds under `docs/specs/<feature-id>/reviews/<mode>-v<N>.json`.
