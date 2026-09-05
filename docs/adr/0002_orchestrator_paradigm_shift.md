# Orchestrator Paradigm Shift

This Architecture Decision Record supersedes all previous implementation plans (like rev9).

## Context
Previously, the orchestrator relied on `fcntl` locks, filesystem attempt counters, and state persistence to manage retries and concurrent executions. This introduced complexity, fragility, and platform dependency (e.g. `fcntl` locks behaving differently across environments).

## Decision
We are shifting to a Stateless Orchestrator Paradigm. The python script (`peer_review.py`) is now completely stateless.

*   All `fcntl` locks and filesystem attempt counters are removed.
*   State persistence is handled by the AI Agent managing the retry loops in memory.
*   The AI Agent is responsible for tracking its own attempt counter and orchestrating the sequence of operations.

## Consequences
*   Simplifies the python script significantly.
*   Removes platform dependencies related to file locking.
*   Puts the burden of state management and retry logic on the calling Agent, which is better equipped to handle complex flows and decision-making during the review process.
