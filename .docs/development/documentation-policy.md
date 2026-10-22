# Documentation policy
## Required per change
- Explain why a module exists, its public inputs/outputs, invariants, side effects and expected failures.
- Update execution-flow and code-map documents when control flow or module layout changes.
- Update API/contracts, configuration and migrations when interfaces or persistence change.
- Record test commands/results and known gaps in handoff; never present unrun checks as passing.
- Add an ADR for a durable architecture choice or supersede an existing ADR for a change.
- Keep examples synthetic. Explain domain terms in the learning guide.
- Keep docs close to behaviour: source docstrings for local contracts, linked docs for cross-module flow. Avoid brittle line-by-line code narration.

## Feature document template
Status and milestone:
Business purpose:
Terms in simple language:
Actual source files/symbols:
Entry point and caller:
Inputs and validation:
Execution steps and state changes:
Outputs:
Tenant/auth boundary:
External effects and idempotency:
Failures/recovery:
Configuration and secrets (names only):
Tests and reproducible example:
Known limitations:
Related ADRs:

## ADR template
Number/title; date; status (proposed/accepted/superseded); context; decision; alternatives; consequences; verification; superseded-by link if applicable.
Accepted means the project's intended design, not proof of implementation.

## Handoff template
Current milestone; implemented files/features; checks executed and outcomes; unavailable checks; pending decisions/blockers; next concrete task; related documents.
Keep handoff concise and replace stale current-state statements; preserve architectural history in ADRs.
