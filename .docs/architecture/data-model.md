# Data model and ownership
## Authoritative sources
ERP owns SKUs, current prices, stock and final order records. The platform owns enquiry workflows, quotation snapshots, approvals, delivery intents and audit history.
A quote stores the exact commercial values reviewed, their source and timestamp. This is evidence, not a second live inventory system.
Synthetic ERP fixtures are replaceable test infrastructure.

## Implemented tables (M0-M6)
| Table | Contents and rules |
|---|---|
| tenants | Business ID and name; RLS by `id` |
| memberships | Tenant, authenticated subject, role (checked list); unique per tenant/subject/role; tenant FK; RLS by `tenant_id` |
| tenant_pricing_policies | One current policy per tenant: version, currency, minor units, rounding mode, tax rate numeric(7,6), max price/stock age; RLS by `tenant_id` |

All three use forced RLS on `app.tenant_id`. The runtime role has SELECT only; the owner role seeds and migrates. Policy history (keeping old versions) is not implemented yet.

### Added in M2
| Table | Contents and rules |
|---|---|
| api_keys | Tenant, name, role (incl. `intake_service`), SHA-256 of secret, revoked_at. API role sees only the presented key (`api_key_lookup` policy) |
| inbox_events | Canonical envelope (JSONB), payload fingerprint, received_at, correlation ID; unique (tenant, channel, connection, provider event ID) |
| enquiries | Tenant, inbox event (composite tenant FK, unique), channel, status (`received`, `ready_for_extraction`, `needs_review`), customer reference, text |
| attachments | Tenant, enquiry (composite tenant FK), display filename, declared/detected type, size, SHA-256, status, rejection reason, storage key |
| jobs | Tenant, kind, payload (references only), status, attempts/max, run_at, lease token/expiry, last error (type only), correlation ID |

All use forced tenant RLS. The worker role additionally sees all `jobs` rows (`worker_queue` policy) to claim work. Composite `(tenant_id, id)` foreign keys stop a child row pointing at another tenant's parent.

### Added in M3
| Table | Contents and rules |
|---|---|
| workflow_runs | Tenant, enquiry (composite tenant FK), graph version (unique per enquiry), status, outcome JSON (items, matches, lines, questions, review reasons). The run ID is the LangGraph thread ID. API can read; worker writes |
| checkpoints, checkpoint_blobs, checkpoint_writes, checkpoint_migrations | LangGraph's own schema (frozen copy). No tenant column, so no RLS: only the worker role has access, and only through a workflow_runs row. API and public access revoked |

Enquiry statuses now also include `ready_for_quotation` and `needs_clarification`.

### Added in M4 (migration 0005)
| Table | Contents and rules |
|---|---|
| quotations | One per enquiry (unique tenant+enquiry): status (`pricing_failed`, `pending_approval`, `revision_requested`, `revision_submitted`, `approved`, `rejected`), current version, pricing issues |
| quotation_versions | Immutable snapshot JSON (lines, ERP price/stock evidence, policy, totals as strings), SHA-256 content hash, currency, total, created_by, reason, revision command ID (unique). Append-only: no UPDATE/DELETE grant, and a trigger also blocks the owner |
| approval_tasks | One per version (unique): version, content hash, status pending/approved/rejected/revision_requested |
| approval_decisions | At most one per task; command ID unique per tenant; actor, action, reason, transport, evidence reference, content hash, timestamps. Append-only |
| channel_enrollments | One-time code hash, subject, channel, expiry, consumed time |
| channel_bindings | Subject linked to (channel, connection, external user); one active binding per account (partial unique index); revocable |
| approval_action_refs | Token hash per task and binding (unique), expiry, sent and consumed times |
| user_sessions | Portal sessions (no tenant): token hash, subject, provider, expiry, revocation. The API sees only the row whose hash it presents |

workflow_runs also records `approved` / `rejected` for the `quotation-approval-v1` graph.

### Added in M5 (migration 0006)
| Table | Contents and rules |
|---|---|
| quotation_documents | Approved PDF of one version (unique tenant+quotation+version+kind; tenant FK to the version): storage key, PDF SHA-256, size, renderer version, source content hash. Append-only: grants plus the `reject_change()` trigger |
| quotation_deliveries | Outbox per target (unique tenant+quotation+version+channel+recipient): status `pending`/`sending`/`available`/`sent`/`failed`/`unknown`, document, provider reference, last error (short), delivered and first-download times. Worker may update only progress columns; API only `first_downloaded_at` |

The PDF bytes live in private object storage (`tenants/<t>/documents/<id>`), not in the database.

### Added in M6 (migration 0007)
| Table / column | Contents and rules |
|---|---|
| tenant_pricing_policies.quote_validity_days | Days an issued quotation can be answered (default 7, at least 1) |
| quotation_documents.valid_until | Printed on the PDF; existing M5 rows were backfilled with created_at + 7 days |
| quotation_responses | Answer to an issued version: outcome (`accepted`, `declined`, `refused_changed`, `withdrawn`, `expired`), actor, reason, differences, revised version, idempotency key (unique per tenant) and fingerprint. Append-only. At most one closing outcome per quotation (partial unique index) |

Quotation and workflow-run statuses gain `accepted`, `declined`, `expired` and `withdrawn`.

### Added in phase 1 (migration 0008, ADR 0018)
| Table / column | Contents and rules |
|---|---|
| connections | One business's configured tool: provider key, name, purposes (`customer_messages`, `manager_approvals`, `catalogue`; later `payments`, `orders`), non-secret `config`, `secret_refs` (references into the secret store, never values), provider-side `account_ref` (unique per tenant and provider; `api-key:<id>` for API keys, `simulated-local` for the demo phone), webhook token SHA-256 (NULL = no webhook), status (`setting_up`, `active`, `error`, `disabled`), last error. Forced RLS. At most one active catalogue source per business (partial unique index). The API may read one row by ID for the webhook route (`connection_hook_lookup`, like `api_key_lookup`). Only the owner writes in phase 1 (API keys, seed) |
| connection_events | Append-only audit (`created`, `migrated`, `status_changed`, ...), actor, detail without secrets |
| inbox_events | Gains `event_type` (`customer_message`, `manager_action`, `delivery_status`, `consent_change`), `connection_ref` (composite FK, NOT NULL), `processed_at`, `outcome`. The dedupe key becomes (tenant, connection_ref, provider event ID, event type). `channel`/`connection_id` stay filled (deprecated). Envelopes gained `reply_to` |
| channel_bindings | Gains `connection_ref` (NOT NULL); one active binding per (tenant, connection, external user). Bindings on a connection that is not active get no approval requests |
| channel_enrollments | Gains `connection_ref` (NULL: any connection of the provider; set: only that one) |

### Added in phase 1 (migration 0009, ADR 0018)
| Table / column | Contents and rules |
|---|---|
| outbound_messages | Everything we send: connection, provider key (copy), purpose, template key, IDs-only params, rendered fixed wording (never an action token), metadata, recipient, idempotency key (unique per tenant: `quotation-delivery:<id>`, `approval-request:<task>:<binding>`, `response-notice:<response>:<binding>`), status (`pending`, `sending`, `available`, `sent`, `delivered`, `failed`, `unknown`), provider message ID (unique per connection), last error, links (document, quotation, version, task, binding, enquiry, response). Forced RLS. Worker: SELECT, INSERT and UPDATE of progress columns only; API: SELECT |
| quotation_deliveries.outbound_message_id | The message carrying the delivery out; the delivery mirrors its status (`delivered` shows as `sent`) |

Backfill (0008): one `api` connection per API key (disabled if the key is revoked), one `simulated` connection per (tenant, connection) used by bindings, a disabled safety-net connection for any other inbox source. Creating an API key also creates its connection; revoking it disables the connection. The demo seed gives each demo business one `simulated` connection for manager approvals and its demo catalogue.

### Added in phase 2 (migration 0010, ADR 0019)
| Table / column | Contents and rules |
|---|---|
| users | A person: `subject` (unique; `user:<uuid>` for sign-ups, the email for demo people), email as typed and normalised (unique when set), display name, verified and disabled times. Global (no tenant); narrow policies by `app.subject`, `app.user_email`, `app.user_id` or membership of the current business. `memberships.subject` references it |
| user_credentials | Argon2id hash per person. API role only for `app.user_id`; the worker has no access |
| email_verifications, password_resets | One open link per person: address, token SHA-256 (set by the worker when sending), email status, expiry, sent/consumed/revoked times |
| account_notices | Emails without a link ("account exists", "password changed") with their send status |
| invitations | Business, address, roles (people roles only), inviter, token SHA-256, email status, expiry, accepted/revoked; one open invitation per address and business |
| admin_events | Append-only audit of administration: actor, action, target, old/new values (never secrets) |
| tenant_profiles | PDF details: legal name, address, tax ID label and value, logo key and hash, version (optimistic locking) |
| rate_limit_counters | Rule, SHA-256 of the key, window start, hits, expiry |
| tenants (new columns) | `status` (`setting_up`, `active`, `suspended`; trigger: the API may only go live), country, time zone, created_by, went_live_at, updated_at |
| tenant_pricing_policies (changed) | The six commercial values may be NULL until saved ("set later"); `updated_by` |
| api_keys (new columns) | created_by, revoked_by |
| jobs.tenant_id | NULL allowed only for `send_account_email` |

Backfill (0010): one person per existing membership subject (never verified), existing businesses `active` with `went_live_at = created_at`, an empty profile each.

## Planned entities
| Entity | Important contents |
|---|---|
| Tenant / membership | Business ID, configuration version; user, tenant, role |
| Connection | Tenant, provider, external account mapping, secret reference, capabilities |
| Contact identity | Tenant, channel, external identity, verified contact linkage |
| Manager channel binding | Tenant, internal membership, connection, external actor, allowed context, verification and revocation status; separate from customer identity |
| Inbox event | Deduplication key, receipt status, normalized payload/reference |
| Enquiry | Tenant, customer, requested items/date, status, correlation ID |
| Workflow run | Tenant, enquiry, graph version, opaque thread ID, state version |
| Quotation / quotation version | Immutable lines, Decimal totals, currency, policy/source evidence, expiry, content hash |
| Approval | Tenant, quotation version/hash, approver, decision, reason, validity, timestamp |
| Approval action reference | Task/version, intended actor/connection, expiry, consumed status; opaque external reference |
| Acceptance | Exact quotation version, verified customer evidence, expiry and processing state |
| Order operation | Idempotency key, external reference, reservation ID, result/reconciliation status |
| Job / outbox | Tenant, operation ID, due time, attempts, lease, next retry, payload reference |
| Document | Tenant, object key, checksum, content type, retention and associated version |
| Audit event | Tenant, actor, action, target/version, outcome, timestamp, correlation ID |

Future negotiation case/round records are planned in [negotiation](../plan/negotiation.md); they are not part of the initial implemented schema. Approval audit also records transport and verified interaction evidence references without storing reusable secrets.

## Constraints
Tenant-owned records have non-null tenant IDs; unique keys include tenant and appropriate connection identifiers.
Tenant-safe foreign keys prevent linking a quotation to another tenant's customer.
One accepted decision per approval/version under concurrency; one order operation per accepted version plus a purchase-level guard across quote revisions. Creating a distinct repeat purchase requires an explicit new purchase identity.
Money uses Decimal and database numeric fields; ISO currency and explicit rounding policy accompany values.
Quantities carry units; timestamps use UTC, while customer locale/timezone remains explicit for date interpretation.
Relative dates such as "next Friday" need receipt timezone context and clarification when delivery intent remains ambiguous.

## Isolation
Authentication determines permitted tenant context; request parameters cannot grant membership.
Repositories require tenant context. PostgreSQL RLS is defense in depth using a non-owner application role; pool transactions must set/reset tenant context safely.
Do not assume LangGraph checkpoint tables automatically inherit business RLS: access only through an authorized run mapping, restrict database credentials, and test thread/checkpoint reads and resumes across tenants.
Storage keys, signed downloads, job payloads, logs, caches and secret references need equivalent tenant checks.
Migration/admin roles are separate from runtime roles. Cross-tenant support access is explicit and audited.
Retention/deletion covers primary records, raw messages, documents, checkpoints, traces and backup expiry policies.
