# Future quotation negotiation
Status: planning only. Implement after the core release/learning milestones. User confirmed that every revised negotiation offer requires manager approval; AI must not negotiate autonomously.

## Actors and purpose
The tenant is the selling business. Its customer receives the quotation and may ask for a lower price, a different quantity or changed terms. This document describes that customer-to-business negotiation, separate from a manager requesting changes to an unsent draft.

## Intended flow
1. Receive a response through any supported customer channel and correlate it to a customer, quotation and version.
2. Distinguish acceptance, rejection, clarification and counteroffer. Uncertainty requires clarification; "too expensive" is not acceptance.
3. Record the requested change and pause ordinary sales follow-ups while the case is under review.
4. Retrieve current approved pricing and applicable tenant rules. Evaluate proposed changes with deterministic calculations.
5. Prepare a proposal for the manager or escalate missing/unsupported terms. AI cannot send a revised offer or commit concessions without manager approval, including changes within configured discount limits.
6. When authorized, create a new immutable quotation version, obtain required approval, generate its PDF and send it through the existing delivery service.
7. Wait for acceptance or another counteroffer, with configured round/deadline limits.
8. Verify acceptance of the exact current offer, then run the existing order revalidation/creation flow.

## Planned records and extension points
Negotiation case: tenant/customer, original quote/version, status, policy version and deadline.
Round: source event, requested terms, proposal values, rule evaluation, actor, resulting quote version and decision evidence.
Cases reference existing quotation, approval and acceptance records; negotiation does not own a separate price engine or order writer.
Suggested case states: requested, under_review, proposal_pending, offer_sent, accepted, declined, expired, escalated. Exact state transitions are finalized at implementation.

## Decisions required before implementation
- Manager approval of every revised offer is settled and mandatory; define assignment/delegation without removing that requirement.
- Permitted discounts and authoritative policy source; margin rules only where reliable cost data exists.
- Negotiable terms (price, quantity, delivery, payment terms), maximum rounds and escalation ownership.
- Whether an original offer remains valid while a counteroffer is pending, and when a replacement withdraws it.
- Customer identity/correlation requirements and human takeover/resume rules.
Do not invent thresholds, grace periods or margin floors. Configured limits validate proposals; they never replace manager approval.

## Related future manager operations
Implement [manager enquiries and commercial commands](manager-operations.md) alongside this milestone: stock questions, price-change requests and discount requests through email or supported messaging channels. Reuse the same quotation and approval services.

## First-release handling before this feature exists
Recognize or allow an operator to mark negotiation requests, place the enquiry in human review, and stop inappropriate acceptance/order handling and ordinary automated follow-ups. Do not autonomously change or send commercial terms. Existing manual revision/approval remains available.

## Later acceptance tests
Test missing policy/cost data, unauthorized concessions, currency/unit errors, requested delivery changes, duplicate counteroffers, expired offers, approval/version invalidation and incorrect customer correlation.
Serialize negotiation against acceptance/order commitment. Once an order is committed, route subsequent requested changes to an explicit order-change review rather than mutating the accepted quote/order.
Test policy-configured behaviour when the customer accepts an old offer during negotiation; do not silently substitute the new price.
