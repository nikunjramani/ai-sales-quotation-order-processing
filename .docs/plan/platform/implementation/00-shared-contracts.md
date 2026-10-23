# Implementation plan, part 0: shared contracts
**Status:** planning document (2026-10-23). It fixes the names, interfaces, tables and numbering that every phase plan ([phase 1](phase-1-foundations.md) … [phase 7](phase-6-7-pilot-source-and-orders.md)) must use, so the phases fit together. If a phase plan needs to change something here, it must change it **here** and say so.

Decisions referenced (D1…D24) are in [../07-decisions-needed.md](../07-decisions-needed.md).

## 1. Vocabulary in code
| Concept | Python name | Table | Replaces / notes |
|---|---|---|---|
| A kind of tool (adapter package) | `Provider` (protocol), `ProviderKey` (str) | — (registry in memory) | Today's `Channel` / `ApprovalChannel` enums |
| A business's configured tool | `Connection` | `connections` | Today's free-text `connection_id` strings |
| What a connection is used for | `Purpose` (`StrEnum`: `customer_messages`, `manager_approvals`, `catalogue`; later `payments`, `orders`) | `connections.purposes` (text[]) | — |
| Provider capability flags | `Capabilities` (frozen dataclass) | — | — |
| Normalised inbound event | `InboundEvent` (union of `CustomerMessage`, `ManagerAction`, `DeliveryStatus`, `ConsentChange`) | `inbox_events` (extended) | `InboundEnvelope` becomes the payload of `CustomerMessage` |
| Outgoing message | `OutboundMessage`, outbox row | `outbound_messages` | `DeliveryChannel.deliver` and `ApprovalNotifier.send_*` become uses of it |
| Message wording | `TemplateKey` (`StrEnum`) + `render_template()` | — (code, fixed wording) | `render_review_text`, `notice_text` |
| Customer | `Contact`, `ContactIdentity` | `contacts`, `contact_identities` | `enquiries.customer_reference` (kept, mapped) |
| Thread | `Conversation`, `ConversationMessage` | `conversations`, `conversation_messages` | — |
| Product data source | keep `ErpReader` (port name), docs say "catalogue source" | — | Hardcoded `SimulatedErp` |
| Our product tables | `LocalCatalogue` (adapter implementing `ErpReader`) | `catalogue_products`, `catalogue_prices`, `catalogue_stock` | — |
| Person who signs in | `User` | `users` | Bare `subject` strings |
| Secret store | `SecretStore` (port) | `connections.secret_refs` (JSON of references only) | Global `QUOTATION_*` provider settings |

"Channel" is no longer used for new code. Existing columns named `channel` keep their name but hold a `ProviderKey` (e.g. `api`, `simulated`, `telegram`).

## 2. Module layout (backend, `src/quotation_app/`)
Follows the existing layers enforced by `tests/unit/test_architecture.py`. Domain, ports and application use the standard library only.
| Layer | New modules |
|---|---|
| `domain/` | `connections.py` (Purpose, Capabilities, ConnectionStatus, validation), `messages.py` (OutboundMessage, MessageStatus, TemplateKey, render_template), `contacts.py` (Contact, ContactIdentity, Consent), `conversations.py` (Conversation, ConversationMessage, intent result), `accounts.py` (User, Invitation, password policy), `catalogue_admin.py` (product editing rules) |
| `ports/` | `providers.py` (Provider protocol, ProvisionResult, PendingAction, InboundRequest), `connections.py` (ConnectionStore), `secrets.py` (SecretStore), `messages.py` (MessageOutbox, MessageSender), `contacts.py`, `conversations.py`, `accounts.py` (UserStore, PasswordHasher, InvitationStore, Mailer), `catalogue_admin.py` (CatalogueStore) |
| `application/` | `providers.py` (ProviderRegistry), `connections.py` (ConnectionService: enable/disable/test), `inbound.py` (InboundService: verify, dedupe, route), `messaging.py` (OutboundService + SendMessageHandler job), `conversations.py` (ConversationService, IntentRouter), `accounts.py` (SignupService, LoginService, InvitationService, BusinessService), `catalogue_admin.py` (ProductService), `catalogue_sources.py` (per-tenant ErpReader resolution) |
| `adapters/providers/` | One sub-package per provider: `api/`, `simulated/`, `web_chat/`, later `twilio_whatsapp/`, `twilio_sms/`, `sendgrid_email/`, `telegram/`, `meta_instagram/`, `meta_messenger/` |
| `adapters/secrets/` | `local.py` (dev: encrypted file/DB with a key from `.env`), `cloud.py` (cloud secret manager, chosen by setting; D8) |
| `adapters/accounts/` | `password.py` (Argon2id hasher), `mail/` (Mailer adapters for sign-up/invite emails: `console` dev, `sendgrid` later) |
| `adapters/catalogue/` | `local.py` (LocalCatalogue, an `ErpReader` over our tables) |
| `persistence/` | `connections.py`, `messages.py`, `contacts.py`, `conversations.py`, `accounts.py`, `catalogue.py` |
| `api/` | `hooks.py` (generic inbound route), `connections.py`, `accounts.py` (sign-up/login/invites), `business.py` (business settings), `catalogue.py`, `conversations.py`, `public_chat.py` (website chat public API) |

**New third-party packages** (adapters only, added to the architecture allow-list when introduced, versions ≥ 14 days old): `argon2-cffi` (passwords, phase 2), `cryptography` (already a transitive dependency; local secret encryption, phase 1), provider SDKs only inside their provider package (e.g. `twilio`, phase 5), `python-multipart` only if file uploads need it.

## 3. The Provider contract (phase 1 defines it; every tool implements it)
```python
class Provider(Protocol):
    key: str                      # "telegram", "web_chat", "api" … unique
    display_name: str
    purposes: frozenset[Purpose]  # what it can serve
    capabilities: Capabilities
    config_model: type            # Pydantic model; the portal renders forms from its JSON schema

    def provision(self, conn: Connection, secrets: SecretStore) -> ProvisionResult: ...
    def deprovision(self, conn: Connection, secrets: SecretStore) -> None: ...
    def test(self, conn: Connection, secrets: SecretStore) -> TestResult: ...
    def verify_inbound(self, conn: Connection, secrets: SecretStore, request: InboundRequest) -> None: ...  # raises InboundRejected
    def parse_inbound(self, conn: Connection, request: InboundRequest) -> list[InboundEvent]: ...
    def send(self, conn: Connection, secrets: SecretStore, message: RenderedMessage) -> SendReceipt: ...  # raises SendRejected / SendUncertain
```
- Unsupported operations raise `OperationUnsupported` (explicit, tested).
- `ProvisionResult` = `ready` (with public details like a phone number or chat link) **or** `needs_action` with a `PendingAction` the portal can show without provider code: `open_url` (pop-up, e.g. Meta Embedded Signup), `show_steps` (text steps, e.g. Telegram), `fill_form` (JSON schema, e.g. SMS registration).
- **Discovery:** Python entry points, group `quotation_app.providers`. `ProviderRegistry.load()` reads them at start-up (API and worker). The `api`, `simulated` and `web_chat` providers live in this repository and register through the same entry points (`pyproject.toml [project.entry-points."quotation_app.providers"]`).
- **Contract tests:** `tests/unit/providers/test_provider_contract.py` runs every registered provider through the same checks (forged signature refused, duplicate event, send outcome mapping, unsupported operations explicit, tenant isolation of parsing).

## 4. Tables and migration numbers
One Alembic migration per phase step, continuing from `0007_acceptance`. Every business table: `tenant_id` + forced row-level security using the existing `_TENANT_FILTER`, explicit grants per role (`quotation_app`, `quotation_worker`), column-level UPDATE grants, append-only tables protected by the existing `reject_change()` trigger.
| Migration | Phase | Tables / changes |
|---|---|---|
| `0008_connections` | 1 | `connections`; `connection_events` (audit of enable/disable/test, append-only); `inbox_events` gains `event_type`, `connection_ref` (FK to connections) and the dedupe key becomes (tenant, connection_ref, provider_event_id, event_type); `channel_bindings` gains `connection_ref`; backfill: one `api` connection per existing API key subject and one `simulated` connection per tenant with bindings |
| `0009_outbound_messages` | 1 | `outbound_messages` (outbox: pending/sending/sent/delivered/failed/unknown; idempotency key; template key; recipient; connection; links to quotation/task/enquiry); existing `quotation_deliveries` stays and is linked (`outbound_message_id`), no data loss |
| `0010_accounts` | 2 | `users`; `user_credentials` (password hash); `email_verifications`; `password_resets`; `invitations`; `tenants` gains `status`, `country`, `time_zone`, `created_by`; `tenant_profiles` (PDF details); function `create_business(...)` (SECURITY DEFINER, owner) |
| `0011_catalogue` | 3 | `catalogue_categories`, `catalogue_products`, `catalogue_prices` (history, effective dates), `catalogue_stock`; `pg_trgm` extension and indexes |
| `0012_conversations` | 4 | `contacts`, `contact_identities`, `conversations`, `conversation_messages`; `enquiries` gains `conversation_id`, `contact_id`; `workflow_runs` gains `round`; customer action references (`customer_action_refs`) |
| `0013_provider_state` | 5 | Only if a provider needs its own state (e.g. Twilio subaccount ID, Meta asset IDs) beyond `connections.config`; otherwise none |
| `0014_orders` | 7 | Decided in the orders phase (questions first) |

## 5. Job kinds (added to `domain/jobs.py` `JobKind`)
| Kind | Phase | Purpose |
|---|---|---|
| `send_message` | 1 | Send one `outbound_messages` row through its provider |
| `provision_connection` | 1 (used from 5) | Run a provider's `provision` in the background |
| `process_inbound` | 1 | Route one stored inbound event (customer message, manager action, status) |
| `send_account_email` | 2 | Verification, invitation and password-reset emails |
| `poll_connection` | 5 | Providers that poll instead of webhooks |
Existing kinds stay; `deliver_quotation` and `notify_approvers`/`notify_response` are re-implemented on top of `send_message` in phase 1 without changing their external behaviour.

## 6. Permissions (added to `domain/tenancy.py`)
| Permission | Roles | Phase |
|---|---|---|
| `integrations:manage` | administrator | 1 (used in 5) |
| `members:manage` | administrator | 2 |
| `catalogue:manage` | administrator, sales_operator | 3 |
| `conversations:view` | administrator, sales_operator, approver, viewer | 4 |
Existing `tenant:manage` covers business settings.

## 7. Portal features (`portal/src/features/`)
Each new feature follows `.docs/development/portal-architecture.md` (model / api / services / store / hooks / ui / routes / index) and the architecture test.
| Feature | Phase | Screens |
|---|---|---|
| `connections` (replaces `channels`) | 1 (list) / 5 (Enable cards) | Connections list, Enable switch per provider, pending-action panel, my linked accounts |
| `account` | 2 | Sign up, verify email, log in, forgot/reset password, profile |
| `business` | 2 | Create business, settings (business, pricing, validity, PDF details), members & invitations, API keys, setup checklist, Go live |
| `catalogue` | 3 | Product list with search, add/edit product, categories, prices, stock |
| `conversations` | 4 | Inbox, conversation detail, contacts |
Public website chat widget: a separate small bundle `portal/src/widget/` (phase 4) built to `widget.js`; it must not import portal features.

## 8. Rules every phase follows
- Generic integrations: no `if provider == …` outside a provider package; no provider-named settings.
- Ask, don't assume: anything not decided in [../07-decisions-needed.md](../07-decisions-needed.md) is listed as an open question in the phase plan, not decided in code.
- Tests in the mirrored `tests/` tree; PostgreSQL integration tests for every migration (upgrade, downgrade, upgrade with data).
- Honest outcomes: unknown send/provider outcomes become `unknown`, never retried automatically.
- Each phase ends with: all tests green, evaluation green, a live run, docs (feature doc, ADR if architecture changes, configuration, handoff).
