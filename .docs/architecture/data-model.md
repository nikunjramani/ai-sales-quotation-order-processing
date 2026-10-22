# Data model and ownership
## Authoritative sources
ERP owns SKUs, current prices, stock and final order records. The platform owns enquiry workflows, quotation snapshots, approvals, delivery intents and audit history.
A quote stores the exact commercial values reviewed, their source and timestamp. This is evidence, not a second live inventory system.
Synthetic ERP fixtures are replaceable test infrastructure.

## Planned entities
| Entity | Important contents |
|---|---|
| Tenant / membership | Business ID, configuration version; user, tenant, role |
| Connection | Tenant, provider, external account mapping, secret reference, capabilities |
| Contact identity | Tenant, channel, external identity, verified contact linkage |
| Inbox event | Deduplication key, receipt status, normalized payload/reference |
| Enquiry | Tenant, customer, requested items/date, status, correlation ID |
| Workflow run | Tenant, enquiry, graph version, opaque thread ID, state version |
| Quotation / quotation version | Immutable lines, Decimal totals, currency, policy/source evidence, expiry, content hash |
| Approval | Tenant, quotation version/hash, approver, decision, reason, validity, timestamp |
| Acceptance | Exact quotation version, verified customer evidence, expiry and processing state |
| Order operation | Idempotency key, external reference, reservation ID, result/reconciliation status |
| Job / outbox | Tenant, operation ID, due time, attempts, lease, next retry, payload reference |
| Document | Tenant, object key, checksum, content type, retention and associated version |
| Audit event | Tenant, actor, action, target/version, outcome, timestamp, correlation ID |

## Constraints
Tenant-owned records have non-null tenant IDs; unique keys include tenant and appropriate connection identifiers.
Tenant-safe foreign keys prevent linking a quotation to another tenant's customer.
One accepted decision per approval/version under concurrency; one order operation per accepted version.
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
