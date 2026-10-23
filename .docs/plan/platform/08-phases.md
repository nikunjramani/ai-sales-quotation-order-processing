# 8. Phases
Each phase is shippable, keeps all existing tests green, and ends with a live demo and documentation (AGENTS.md). The order is a proposal (D23). Decisions each phase needs are listed. **No phase starts until its decisions are answered.**

| Phase | Delivers | Needs decisions | Verified by |
|---|---|---|---|
| **1. Foundations (refactor, no new features)** | Provider registry by entry points; `connections` table with encrypted secrets; one generic webhook route; `outbound_messages` outbox and templates; per-business catalogue source resolution (no more hardcoded `SimulatedErp`). Today's API intake, pull delivery and simulated phone move onto it as providers `api` and `simulated` | D8 | All existing tests (unit, PostgreSQL, evaluation) unchanged; new provider contract tests; the demo page still works end to end |
| **2. Accounts and onboarding** | Real login (OIDC), users table, sign-up, "create your business" (narrow database function), members and invitations, settings screens (business, pricing, validity, API keys), setup checklist, "Go live" | D1-D3 | New business from zero to a test enquiry without scripts; isolation tests between two self-created businesses |
| **3. Product data** | Our catalogue tables; spreadsheet import with column mapping and row errors; manual product editor; "local catalogue" source; better search (full-text + similarity) | D18, D19 | Contract tests pass for the local source; import of a 1,000-row synthetic file; quotations priced from it; stale stock flagged |
| **4. Customers and conversations + website chat** | Contacts, identities, conversations, messages; follow-up linking (the "10 meter?" case); questions and quotations sent back; customer accept/decline via signed actions; website chat widget (first real tool); portal inbox | D11-D15, D22 | The demo transcript from 2026-10-23 completes in one enquiry; a website chat enquiry reaches approval and the customer accepts in the chat |
| **5. First external tools** | Telegram (customers + manager buttons), then email; WhatsApp and Instagram when accounts and reviews are ready | D5-D7, D9, D10 | Provider contract tests + a sandbox run per tool; a manager approves from Telegram; spoofed or replayed webhooks refused |
| **6. Real product source for the pilot** | Connector (live or sync) for the pilot business's ERP or shop | D21 | Contract tests against its sandbox |
| **7. Orders (M6b)** | Order from accepted quotation, status events, customer updates, "track my order", ERP write with reconciliation if supported | Orders questions (asked then) | Duplicate-safe orders; unknown outcomes reconciled; status updates reach the customer's tool |
| **Later** | Payments; our own inventory; negotiation (M11) | Asked when started | — |

## Rough size (for planning, not a promise)
- **Phase 1:** large refactor, mostly invisible; the foundation for everything else.
- **Phases 2, 3 and 4:** about the size of a past milestone each (M4-M6).
- **Phase 5:** small per tool once phase 1 exists; WhatsApp/Instagram take longer only because of Meta's business verification.

## What stays the same throughout
- The quotation core (reading, matching, pricing, approval, PDF, acceptance) and its tests.
- The layered structure, tenant isolation and the "ask, don't assume", "generic integrations" and "permission before commit/push" rules.
