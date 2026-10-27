# Detailed implementation plan
**Status:** planning only (written 2026-10-23 to 2026-10-26); nothing here is built. It turns the [platform plan](../README.md) into step-by-step work a developer can follow:
- every file to add or change, with `file:line` references to today's code;
- signatures, tables, row-level security and grants;
- API shapes, portal screens and jobs;
- tests, docs, risks and a definition of done.

## Reading order
| # | Document | What it covers | Size |
|---|---|---|---|
| 0 | [Shared contracts](00-shared-contracts.md) | **Binding** names, interfaces, tables, migration numbers, jobs, permissions, routes and settings for all phases. §8 lists the 3 points that need the owner's decision; §9 records changes | Read first |
| 1 | [Phase 1: foundations](phase-1-foundations.md) | Provider registry, connections, secrets, generic webhooks, one outbox, per-business product source. Today's features move onto it unchanged | Large refactor |
| 2 | [Phase 2: accounts](phase-2-accounts.md) | Email + password sign-up and login, create business, members and invitations, settings, API keys in the portal, setup checklist, Go live | Like a past milestone |
| 3 | [Phase 3: product data](phase-3-catalogue.md) | Our catalogue tables, the product editor in the portal, the local catalogue source, better search | Like a past milestone |
| 4 | [Phase 4: customers and conversations](phase-4-conversations.md) | Contacts, conversations, follow-ups ("10 meter?"), sending questions and quotations back, customer buttons, website chat | Like a past milestone |
| 5 | [Phase 5: one-click providers](phase-5-one-click-providers.md) | Enable flows for email (SendGrid), WhatsApp and SMS (Twilio), Telegram, Instagram, Messenger; AI-read manager replies with the five safety rules; company setup tasks | Small per provider after phase 1 |
| 6-7 | [Phases 6-7: pilot product source and orders](phase-6-7-pilot-source-and-orders.md) | ERP/shop connector for the pilot; orders after acceptance (provisional); payments, tracking and own inventory as extension points. Orders, payments and inventory have **question lists only**, no invented rules | Provisional |

## Questions still open
Each phase plan has a "Decisions used and open questions" section. The questions are technical or detail questions, each with a proposed default marked "to confirm". They block only their own phase:
| Phase | Where | Examples |
|---|---|---|
| 0 | [§8](00-shared-contracts.md#8-points-for-the-user-raised-by-the-phase-plans-not-decided-here) | Who edits products; whether viewers see customer contact details; what "existing tests unchanged" promises |
| 1 | Phase 1, open questions | Keeping the old simulated webhook path as an alias; local secret encryption details |
| 2 | Phase 2, open questions | Password rules, login rate limits and lockout, invitation expiry, email wording |
| 3 | Phase 3, open questions | Required product fields, one currency per business, maximum products |
| 4 | Phase 4, open questions + D13/D14/D15 | Merging contacts, the acknowledgement message, opt-out wording, website chat verification |
| 5 | Phase 5, P5-1 … | Reply approval when no AI model is configured, Meta/Twilio account details, costs to show |
| 6-7 | Phase 6-7, Q1-Q16 and the pilot questions | When an order is created, cancellations, statuses customers see, payment terms; which ERP the pilot uses (D21) |

## How the phases depend on each other
```
Phase 1 foundations ──► Phase 2 accounts ──► Phase 3 product data ──► Phase 4 conversations ──► Phase 5 providers
                                                     └──────────────► Phase 6 pilot source      Phase 7 orders (after 4)
Company tasks (Meta verification, Twilio Tech Provider, app review, domain) run in parallel; they are needed by phase 5.
```
