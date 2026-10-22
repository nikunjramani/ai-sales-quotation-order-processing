# Documentation index
Status 2026-10-22: M0-M2 are complete (local and CI). M3 (requirement extraction) is implemented and verified locally; CI pending until pushed. Business workflow documents describe planned behaviour. See the handoff for verified implementation status.

## Planning
- [Product scope and acceptance criteria](plan/product.md)
- [Milestones from setup to release](plan/roadmap.md)
- [Technology and access requirements](plan/stack-and-access.md)
- [Open decisions and risks](plan/open-decisions.md)
- [Future quotation negotiation](plan/negotiation.md)
- [Future manager enquiries and commercial commands](plan/manager-operations.md)
- [Pre-implementation plan review](plan/readiness-review.md)

## Architecture
- [System boundaries and components](architecture/system.md)
- [System flowcharts](architecture/flowcharts.md)
- [Channel and business-system contracts](architecture/integrations.md)
- [Data ownership and tenant isolation](architecture/data-model.md)
- [Execution flow and recovery](architecture/execution-flow.md)
- [Approval and customer acceptance](architecture/approvals.md)
- [Module boundaries and extension rules](architecture/module-boundaries.md)
- [Architecture decision records](adr/README.md)

## Engineering and operations
- [Local setup walkthrough](development/setup.md)
- [Configuration, roles and API contracts](development/configuration.md)
- [Code map (implemented and planned)](development/code-map.md)
- [Quotation pricing and tenant context (M1)](features/quotation-pricing.md)
- [Enquiry intake, job worker and attachment quarantine (M2)](features/enquiry-intake.md)
- [Enquiry extraction workflow with swappable models (M3)](features/enquiry-extraction.md)
- [Documentation policy and templates](development/documentation-policy.md)
- [Testing and evaluation](development/testing.md)
- [Security and privacy](operations/security.md)
- [Release and recovery runbook](operations/release.md)
- [Learning guide](learning/guide.md)
- [Source references](references.md)
- [Portable agent context](agent-context.md)
- [Current state and next steps](handoff.md)

Read product -> system -> execution flow -> roadmap for a first introduction.
Read agent context -> handoff -> task-specific documents for a returning session.
