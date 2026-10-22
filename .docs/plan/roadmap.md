# Delivery roadmap
Status: M0 complete 2026-10-22 (live migrations, downgrade/re-upgrade, seed, RLS integration tests and API smoke passed locally; fresh-setup [CI run](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39734937763) passed). M1 is next. M1-M11 are not implemented.
Complete each exit gate before claiming the milestone finished. Tests and documentation accompany every milestone.

| Milestone | Deliverables | Dependencies and exit gate |
|---|---|---|
| M0 Foundation | Verify Python/Docker/Git; package and lockfile; CI; PostgreSQL migrations; settings; synthetic tenant fixtures | Fresh setup works using documented commands; secret hygiene; versions verified and pinned |
| M1 Domain and tenancy | Tenant context, role model, product/price/stock contracts, Decimal quotation calculator, simulated ERP | Two-tenant negative tests; rule tests for quantities, rounding, absent price, unavailable stock |
| M2 Intake | Manual/API intake, canonical event schema, inbox dedupe, durable job worker, private attachment storage/quarantine | Replay/race tests; accept only after durable receipt; retries recover after worker crash; unsafe attachments isolated |
| M3 AI and graph | Bounded text/PDF extraction, structured requirements, product matching, LangGraph branches, persistent checkpoints | Synthetic evaluations; unsupported/scanned formats handled explicitly; missing/ambiguous inputs prompt clarification; no invented facts |
| M4 Approval core and portal | Shared approval service, identity/channel-binding contracts, review packets, mobile-friendly portal, immutable versions, simulated channel actions and resume dispatch | Same approve/reject/revise contract through portal and fake adapter; replay, revocation, concurrency and restart tests |
| M5 Quotation delivery and email approval | PDF renderer, object storage, outbox dispatcher, real email sandbox, verified manager reply approval, delivery tracking | Only approved version sent; quote-bound direct replies tested including spoof/quoted/automatic/stale replies; provider timeouts handled; PDFs match approved totals |
| M6 Orders | Customer acceptance, offer expiry/withdrawal rules, price/stock revalidation, reserve/create, reconciliation and order confirmation | Duplicate acceptance across revisions safe; changed terms require approval/acceptance; unknown outcomes never announce success |
| M7 Integrations | Telegram enquiry and in-channel manager approval, first real ERP sandbox, optional CRM/n8n bridge, follow-up jobs | Manager reviews/decides without portal; shared approval contract suite; two customer channels; consent/policy checks; cancelled follow-ups stay cancelled |
| M8 Pilot hardening | Security review, load tests, model cost limits, monitoring, backup/restore, deployment/recovery runbooks | All release gates pass; sandbox-to-production authorization; pilot business validates commercial rules |
| M9 Release | Versioned release notes, migrations, staged rollout, support ownership, production smoke checks | Sign-off record, rollback criteria, measured pilot results, working alerts |
| M10 Expansion | WhatsApp, Instagram and their manager approval capabilities, further ERP/CRM adapters, optional semantic retrieval | Validate provider access/policies, identity and approval contracts, rollout gates per connector |
| M11 Negotiation and manager operations (deferred) | Customer counteroffers, manager stock enquiries and price/discount requests across supported channels, reusing existing services | Start after core learning/release; every negotiated revision requires manager approval; no autonomous negotiation; clarify write scope and test command permissions |

## Execution discipline
M4 review includes full commercial detail; M5 adds draft PDF previews and approved PDFs. M2/M3 attachment handling needs private storage before M5 outbound documents. Manual pause/ownership is delivered with the M4 exception portal and exercised through M6/M7.
For a milestone: explain concepts -> identify acceptance cases -> implement a small vertical slice -> run it -> exercise failures -> update docs and handoff.
Do not install all optional tools in advance. This is sequencing, not removal of requirements.
Do not start real outbound messaging or production ERP writes before sandbox validation and explicit activation.

## Definition of done for release
Core acceptance scenarios pass; production auth replaces local fixtures; tenant isolation is exercised across HTTP, DB, jobs, files and checkpoints; integrations use authorized accounts; migrations and restore are tested; ambiguous remote outcomes reconcile safely; operator instructions are executable; known limitations are published.
The release need not support every vendor, but supported integrations must work end to end.
