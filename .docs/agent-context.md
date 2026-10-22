# Portable agent context
## User intent
Build a reusable multi-business sales quotation/order automation product while learning LangChain, LangGraph and workflow engineering. Explain everything simply. User expects AI-written code to have durable documentation and wants future tools/sessions to recover context.

## Agreed direction
Multiple channel adapters, existing ERP integrations, deterministic commercial rules, internal approval separate from customer acceptance, documentation-first implementation.
Manager review/approval must support configured messaging channels as well as the portal through one shared approval service. Direct email reply approval is confirmed. Provider extensions must not rewrite business rules. Customer negotiation and manager stock enquiries/price-change/discount commands are planned for M11 only. Every negotiated revision requires manager approval; AI must not negotiate autonomously, even within configured limits. Price-change scope must be clarified rather than assuming global ERP writes.
Use PostgreSQL from the foundation, a modular Python application, LangGraph for persisted workflow, and durable jobs/outbox for external effects.
See accepted [ADRs](adr/README.md). These are design commitments. Complete (local and CI): M0 foundation, M1 domain/tenancy (deterministic pricing, roles, tenant context, simulated ERP) and M2 intake (API keys, idempotent enquiry API, job worker, attachment quarantine) and M3 requirement extraction (LangGraph, swappable interpreters, free by default). Next: M4, which needs the OIDC identity provider decision. The user wants free models now and easy provider switching later. See the handoff.

## Constraints
No forced inventory migration. No model-invented prices or stock. No cross-tenant access. No unapproved quotation sends. No blind retries of uncertain order writes.
Plans and ADRs live in [plan](plan/) and [adr](adr/); other code and operations documentation lives in this documentation tree.
Do not rely on conversation memory. Do not silently change scope or defer production requirements because the user is learning.
No delegation is currently authorized.

## Starting prompt for any agent
"Read AGENTS.md, .docs/README.md, .docs/agent-context.md and .docs/handoff.md. Inspect the actual repository. Continue the next agreed milestone, explaining new concepts simply. Update relevant docs and handoff with implementation and verification evidence. Do not assume planned files or integrations exist."

## Skills and tool portability
Repository instructions, ADRs and documented constraints are portable. Installed skills and provider tools are environment-specific and cannot be guaranteed by these files.
Use available applicable skills according to their instructions. If a required capability is unavailable, record the limitation and use an authorized alternative.
No project-specific executable skills have been created in this baseline. If reusable skills are added later, version their instructions and list paths/prerequisites here.
