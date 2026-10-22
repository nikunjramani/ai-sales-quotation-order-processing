# Data model and ownership
## Authoritative sources
ERP owns SKUs, current prices, stock and final order records. The platform owns enquiry workflows, quotation snapshots, approvals, delivery intents and audit history.
A quote stores the exact commercial values reviewed, their source and timestamp. This is evidence, not a second live inventory system.
Synthetic ERP fixtures are replaceable test infrastructure.

## Implemented tables (M0-M2)
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
