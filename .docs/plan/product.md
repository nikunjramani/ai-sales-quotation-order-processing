# Product scope
## Purpose
Help multiple businesses process enquiries from different channels, prepare accurate quotations using existing business systems, obtain approval, and create orders after customer acceptance.

A tenant means one business using the platform. A contact means that business's customer. An internal approver is an employee authorized to approve commercial offers.

## Product rules
- Support tenants with separate identities, credentials, catalogues, policies, documents, and audit histories.
- Channel adapters normalize messages; the core workflow does not assume email.
- ERP/inventory systems remain authoritative. The platform is an automation layer, not a required replacement inventory database.
- Human review is required for quotation sending in the first release.
- Explicit customer acceptance and order revalidation follow internal approval.
- Begin with physical B2B goods and one configured currency per quotation. Mixed currencies, autonomous negotiation, payment execution, manufacturing planning, and shipping execution are outside the first release.
- Tax, delivery, discount, and expiry rules are configured and validated for each pilot business; sample policies are not universal tax advice.

## First release
Core: tenant administration, role-based portal, enquiry handling, product matching, live price/stock lookups, deterministic pricing, versioned quotations, approval, PDF delivery, acceptance, order creation, audit, durable recovery, and follow-up scheduling.
Adapters: authenticated manual/API intake, one real email connector, Telegram as a second channel, simulated ERP and one selected real ERP sandbox connector.
WhatsApp and Instagram: supported architecture and planned adapters; provider onboarding gates their actual delivery. Do not advertise an adapter as supported before contract tests and end-to-end validation pass.
Other ERP/CRM connectors follow demand; an optional CRM connector must not block the core order workflow.

## Observable acceptance scenarios
1. Equivalent email and Telegram requests produce equivalent normalized requirements.
2. Business A cannot access business B's data, files, checkpoints, integrations, or approval links.
3. An ambiguous product triggers clarification; an absent price never becomes zero.
4. Stock unavailable, unknown, stale, and available are distinct results.
5. Approved version 1 cannot authorize changed version 2.
6. Replayed events and repeated acceptance do not produce duplicate orders.
7. A restart during approval preserves the pending request.
8. A timeout after an ERP write triggers reconciliation before another write.
9. An unauthorized or expired approval attempt is rejected and recorded.
10. Follow-ups stop after rejection, acceptance, opt-out, or case closure.
11. A tenant can connect an ERP without manually importing all stock into this platform.
12. Every externally committed action has a traceable actor, version, result, and correlation ID.

## Business onboarding
Create tenant -> assign administrators/approvers -> connect channels and ERP -> map fields, units and currencies -> configure policies -> run sandbox scenarios -> authorize production activation.
