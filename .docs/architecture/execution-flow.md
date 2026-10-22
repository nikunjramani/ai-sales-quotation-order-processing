# Planned execution flow
The sales workflow table below remains a target. M0 only implements the foundation trace described here.

## Implemented M0 trace
1. Uvicorn calls [create_app](../../src/quotation_app/api/app.py); [Settings](../../src/quotation_app/config.py) validates configuration and hides secrets.
2. [build_engine](../../src/quotation_app/persistence/database.py) configures a bounded pool. Creating the app does not connect, migrate or seed the database.
3. GET /health/live returns 200 without a database query.
4. GET /health/ready reads the schema revision and checks the connected role. Missing/unreachable/unmigrated DB, unexpected revision or privileged role returns sanitized 503; a valid connection/schema/role returns 200.
5. Application shutdown disposes the engine.
6. Separately, Alembic uses migration credentials to create the tenant table and RLS. The [seed](../../src/quotation_app/persistence/seed.py) sets transaction-local tenant context and inserts fictional fixtures idempotently; it refuses production mode.
No business HTTP routes, authenticated tenant context, workflow engine or external actions exist yet. Migration, seed, RLS and readiness behaviour were executed against local PostgreSQL on 2026-10-22. See [setup](../development/setup.md).

## Planned sales workflow

| Step | Input and action | Output / failure branch |
|---|---|---|
| 1 Receive | Verify provider authentication and connection; normalize message | Reject invalid event; store inbox event and job atomically before acknowledgement |
| 2 Dispatch | Lease job; resolve tenant/run; serialize execution | Duplicate receipt returns previous status; concurrent jobs wait/retry safely |
| 3 Extract | Read bounded text/attachments; model produces validated requirements | Missing fields -> clarification; unsafe/invalid output -> review |
| 4 Resolve products | Search ERP; select supported matches with evidence | Ambiguous/no match -> ask or review; never invent SKU |
| 5 Retrieve facts | Fetch prices, units, stock and delivery inputs | Missing/stale/failed lookup -> retry or exception; no fallback invented values |
| 6 Calculate | Deterministic Decimal arithmetic and tenant policy | Draft immutable version with calculation explanation |
| 7 Request approval | Shared approval service persists task + review-packet outbox intent for configured manager channels; graph interrupt | Portal or supported in-channel review; pending state survives process restart |
| 8 Resume | Portal/channel adapter submits verified decision to the same approval service; authorized version-bound decision creates resume job | Reject -> closed/revision; approve -> validate and prepare delivery; stale/unauthorized action fails |
| 9 Deliver | Render approved version PDF; persist immutable object; send via outbox | Track acknowledgement/delivery; unknown result -> reconcile |
| 10 Await response | Persist wait and due follow-up jobs | Reply -> correlate; counteroffer -> human review initially, future negotiation module later; reject/expiry/opt-out -> stop follow-ups |
| 11 Accept | Verify customer/version; revalidate ERP facts | Changed material terms -> new quote; duplicate -> existing result |
| 12 Commit order | Reserve if supported; create with stable external reference | Store ERP ID; partial/unknown result -> reconciliation |
| 13 Finish | Persist confirmed ERP order and customer confirmation intent; optional CRM synchronization | Notification/CRM failures retry independently; never recreate successful order or announce unknown outcome as success |

## State design
Store tenant/run/enquiry IDs, normalized requirements, evidence references, quote version, approval/acceptance references, pending operation IDs, status and schema version.
Keep large documents and secrets outside graph state. Checkpoints may contain PII and require retention/access controls.
Business status and checkpoint state are related but separate; UI uses authoritative business records.
Prefer short nodes with explicit input/output contracts. Separate model reasoning from external writes.

## Resume and side effects
Interrupted nodes can run again. No non-idempotent send/order write may rely on "this node ran only once."
Commit stable operation records before calling remote systems; reconcile operation completion on replay.
A crash after decision persistence but before graph resume is recovered from the durable resume job.
A crash after remote success but before local acknowledgement requires reference/status lookup, not blind resend.
Use bounded exponential backoff with jitter, error classification, attempt limits and a visible dead-letter/exception queue.
Jobs use leases, lease renewal for long calls, expiry recovery and fencing/version checks to reject stale worker commits.
Lock/serialize per workflow, including approval and customer reply races. Recheck cancellation/version immediately before an irreversible intent is dispatched.

## Order partial failures
Before automatic order creation, enforce a business-level purchase identity across quote revisions. Repeated acceptance of another version cannot silently create a second order for the same intended purchase. Partial acceptance, quantity edits and substitutions route to reviewed revision until explicitly supported.
If reservation succeeds but order creation fails conclusively, release or expire the reservation according to ERP policy.
If creation outcome is unknown, reconcile before releasing/retrying; do not cancel stock belonging to an order that actually exists.
Record compensating actions and unresolved exceptions for an operator.

## Human ownership and cancellation
Persist manual owner, pause reason and resume authority. Human takeover suspends automated commercial writes and ordinary follow-ups; resume is authorized and audited. Pausing cannot undo a remote operation already sent, so reconcile in-flight/unknown outcomes.
Cancellation/withdrawal before order commitment stops eligible pending actions and invalidates relevant approval/acceptance actions under the configured offer policy. A completed ERP order cannot be undone by editing workflow state: route later changes/cancellation to an explicit human/ERP process.
Preserve the calculation policy snapshot and recheck current permissions at execution. Before M6, define which policy/source changes require recalculation; any material revised offer requires fresh manager approval and customer acceptance.

## Extension routing
Manager channel adapters never resume the graph directly; an accepted decision persists the durable resume intent. Changing approval channels does not change the graph's decision contract.
Negotiation is deferred: see [future negotiation](../plan/negotiation.md). When implemented, its proposals use existing quotation/version/approval/delivery services and serialize against customer acceptance/order commitment.
Every negotiated revision requires manager approval. Future [manager enquiries/commands](../plan/manager-operations.md) route verified stock questions to read-only ERP lookups and scoped price/discount requests to validated proposed revisions; they do not bypass approval or imply catalogue-write authority.

## Workflow upgrades and version compatibility
Persist graph/schema version. Keep compatible handlers for waiting runs or provide tested migrations; never assume a deployment can resume old checkpoints safely.
