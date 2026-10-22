# Future manager enquiries and commercial commands
Status: recorded for M11 alongside negotiation; do not implement now.

## Requested capabilities
Managers can use email, WhatsApp, Telegram or other supported adapters to:
- Ask what stock is available, including a specific product or warehouse.
- Request a price change, for example "change this price to 900".
- Request a discount on a quotation or applicable line.
- Review resulting revisions and approve or reject them through the same channels.
The portal remains available. Channel availability follows verified provider capabilities and tenant setup, not an assumption that every provider supports every operation.

## Execution boundary
Verify the enrolled internal manager and tenant -> classify enquiry versus change request -> resolve product/quote/version and requested scope -> ask for missing details -> check permission -> call the existing business service -> return factual results or a reviewable proposed change.
Read-only stock questions use the ERP adapter with warehouse/unit semantics and a source timestamp; unknown or unavailable stock is stated explicitly. AI does not invent availability.
Change requests carry explicit currency/unit, target scope, expected version and operation ID. Validate limits and recalculate totals deterministically. Return a new quote version for approval rather than silently modifying an approved offer.
An instruction to change a price or add a discount is not automatically approval of the final recalculated quotation. Every negotiated revision must be reviewed and approved by the manager before customer delivery.
Reuse channel adapters, identity bindings, quotation/pricing services, approval service and audit/outbox infrastructure. A later manager-command application module coordinates these contracts; provider-specific logic stays in adapters.

## Scope choices to resolve during implementation
"Change price" may mean one quotation line, a customer price list, or the ERP catalogue's permanent price. Record support for the requested feature, but do not assume permission to alter global prices. Clarify the target before preparing any write; broader ERP price-list updates require explicit scope, capability and authorization design.
Clarify discount type (percentage or amount), line versus whole quote, currency, and any expiry/customer restriction. Missing details require a question, not model guesses.
Decide allowed stock-list breadth, shared-chat disclosure and identity checks before activation. No such unanswered details block recording the feature now.

## Acceptance criteria for later implementation
- Equivalent requests through different adapters invoke the same authorized use case.
- Stock questions never change stock or prices and report source/freshness.
- Ambiguous price/discount scope cannot perform a write; a quote adjustment cannot update the global catalogue.
- Unauthorized, cross-tenant, revoked or replayed manager commands cannot cause duplicate or forbidden changes.
- Revised quotes invalidate previous approval; no customer-facing negotiated revision is sent without manager approval.
- Audit links the originating message, verified actor, exact target/version, proposed result and subsequent decision.
