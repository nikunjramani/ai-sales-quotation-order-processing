# Pre-implementation plan review
Date: 2026-10-22
Outcome: ready to start M0; not a claim of production readiness or complete provider specifications.

## Review coverage
Reviewed product scope, milestone dependencies, channel/ERP boundaries, tenant isolation, approval/version rules, future negotiation and manager commands, persistence, recovery, tests, security, deployment and agent handoff.

## Gaps resolved
| Gap | Resolution and implementation gate |
|---|---|
| Attachment ingestion lacked explicit ownership | M2 provides private attachment storage/quarantine; M3 provides bounded text/PDF extraction and explicit unsupported-file handling. OCR and supported languages/formats must be chosen before claiming scanned-document support. |
| Approval preview versus final PDF was ambiguous | M4 supplies complete commercial review detail through portal/fake adapters. M5 adds immutable draft PDF previews and approved delivery PDFs tied to the same quote version; M7 reuses these for channel approval. |
| Orders ended without customer confirmation | M6 persists a confirmation intent only after confirmed ERP success. Notification retries do not recreate the order; unknown ERP outcomes cannot announce success. |
| Human handoff/cancellation lacked operational rules | Persist manual ownership/pause status; suspend automated follow-ups/writes, audit authorized resume, and reconcile already-started remote operations. Post-order cancellation is a human/ERP process outside first-release automated fulfilment. |
| Ordinary offer expiry/withdrawal rules were underspecified | Before M6, define active-offer and replacement policy, expiry timezone, customer identity and accepted version. Guard order creation across revisions of the same purchase, not just duplicate events for one version. |
| Policy changes during a paused workflow were underspecified | Preserve the policy snapshot used for calculation, recheck current authorization at action time, and define revalidation triggers before M6. Material changes return to approval and customer acceptance. |
| Flowcharts existed only in conversation | Persisted [system flowcharts](../architecture/flowcharts.md) and linked them from the index. |
| Later manager commands absent from proposed code map | Added deferred manager-command location; no implementation in M0. |

## Requirements traced to milestones
| User requirement | Planned delivery |
|---|---|
| Reusable multi-business platform and existing inventory | M1 tenancy/contracts; M7 real ERP sandbox |
| Multiple enquiry channels | M2 API/manual intake; M5 email; M7 Telegram; M10 additional channels |
| Manager approval without mandatory portal visit | M4 shared approval service; M5 verified email replies; M7 Telegram; M10 other supported providers |
| Accurate quotation/PDF and confirmed orders | M1 pricing; M5 PDF/delivery; M6 acceptance/order/confirmation |
| Saved workflows and reliable retries | M2 durable jobs; M3 checkpoints; M4 resume; M6 reconciliation |
| Every negotiated revision approved by manager | Invariant now; feature implementation M11 |
| Manager stock enquiries and scoped price/discount commands | Recorded for M11; no global ERP-write assumption |
| Documentation and portable AI context | Required throughout; architecture, flow, tests and handoff updated with changes |

## Remaining decisions, with owners
Developer/user chooses model/provider budget before M3 and identity provider before M4. Pilot business supplies commercial policies, ERP access/mappings and authorized managers before integration activation. Deployment owner supplies retention/region, capacity targets and recovery objectives before M8.
Exact library versions are selected and locked during M0. Detailed API payloads, DB migrations and executable runbooks accompany their implementation milestones.
Direct email verification must be proven against the chosen provider before enabling it; a sender header alone is insufficient. Provider permissions and Meta channel policies remain verification gates.
See [open decisions](open-decisions.md). None of these prevents local foundation work. Do not claim all future design choices are settled.

## Verification limits
This is a documentation consistency review, not a code/security audit or live integration test. Link/whitespace checks are recorded in the handoff. Diagram source was inspected; rendered diagrams have not been automatically tested.
