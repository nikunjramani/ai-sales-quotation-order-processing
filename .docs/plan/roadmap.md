# Delivery roadmap
Status: every milestone is pending. Documentation exists; application implementation has not started.
Complete each exit gate before claiming the milestone finished. Tests and documentation accompany every milestone.

| Milestone | Deliverables | Dependencies and exit gate |
|---|---|---|
| M0 Foundation | Verify Python/Docker/Git; package and lockfile; CI; PostgreSQL migrations; settings; synthetic tenant fixtures | Fresh setup works using documented commands; secret hygiene; versions verified and pinned |
| M1 Domain and tenancy | Tenant context, role model, product/price/stock contracts, Decimal quotation calculator, simulated ERP | Two-tenant negative tests; rule tests for quantities, rounding, absent price, unavailable stock |
| M2 Intake | Manual/API intake, canonical event schema, inbox dedupe, durable job worker, attachment boundary | Replay/race tests; accept only after durable receipt; retries recover after worker crash |
| M3 AI and graph | Structured extraction, bounded product matching, LangGraph branches, persistent checkpoints | Synthetic evaluation suite; missing/ambiguous inputs route to clarification; no invented commercial facts |
| M4 Approval portal | Identity integration, review screens, immutable versions, approval events, resume dispatch | Authorized approve/reject/revise; restart recovery; expired, stale and cross-tenant attempts fail |
| M5 Quotation delivery | PDF renderer, object storage, outbox dispatcher, real email sandbox, delivery tracking | Only approved version sent; provider timeout handled; uncertain sends visible; PDFs match approved totals |
| M6 Orders | Customer acceptance, price/stock revalidation, reserve/create capabilities, reconciliation | Duplicate acceptance safe; changed terms require new approval/acceptance; partial failures reconciled |
| M7 Integrations | Telegram, first real ERP sandbox, optional CRM/n8n bridge, follow-up jobs | Same workflow across two channels; adapter contract suite; consent/policy checks; cancelled follow-ups stay cancelled |
| M8 Pilot hardening | Security review, load tests, model cost limits, monitoring, backup/restore, deployment/recovery runbooks | All release gates pass; sandbox-to-production authorization; pilot business validates commercial rules |
| M9 Release | Versioned release notes, migrations, staged rollout, support ownership, production smoke checks | Sign-off record, rollback criteria, measured pilot results, working alerts |
| M10 Expansion | WhatsApp, Instagram, further ERP/CRM adapters, optional semantic retrieval | Validate provider access/policies, contract tests and rollout gates per connector |

## Execution discipline
For a milestone: explain concepts -> identify acceptance cases -> implement a small vertical slice -> run it -> exercise failures -> update docs and handoff.
Do not install all optional tools in advance. This is sequencing, not removal of requirements.
Do not start real outbound messaging or production ERP writes before sandbox validation and explicit activation.

## Definition of done for release
Core acceptance scenarios pass; production auth replaces local fixtures; tenant isolation is exercised across HTTP, DB, jobs, files and checkpoints; integrations use authorized accounts; migrations and restore are tested; ambiguous remote outcomes reconcile safely; operator instructions are executable; known limitations are published.
The release need not support every vendor, but supported integrations must work end to end.
