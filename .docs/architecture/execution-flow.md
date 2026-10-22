# Planned execution flow
This is a target flow, not a description of existing code. Update with actual module/symbol links as implementation lands.

| Step | Input and action | Output / failure branch |
|---|---|---|
| 1 Receive | Verify provider authentication and connection; normalize message | Reject invalid event; store inbox event and job atomically before acknowledgement |
| 2 Dispatch | Lease job; resolve tenant/run; serialize execution | Duplicate receipt returns previous status; concurrent jobs wait/retry safely |
| 3 Extract | Read bounded text/attachments; model produces validated requirements | Missing fields -> clarification; unsafe/invalid output -> review |
| 4 Resolve products | Search ERP; select supported matches with evidence | Ambiguous/no match -> ask or review; never invent SKU |
| 5 Retrieve facts | Fetch prices, units, stock and delivery inputs | Missing/stale/failed lookup -> retry or exception; no fallback invented values |
| 6 Calculate | Deterministic Decimal arithmetic and tenant policy | Draft immutable version with calculation explanation |
| 7 Request approval | Persist approval task + outbox intent; graph interrupt | Pending state survives process restart |
| 8 Resume | Authorized version-bound decision creates resume job | Reject -> closed/revision; approve -> validate and prepare delivery |
| 9 Deliver | Render approved version PDF; persist immutable object; send via outbox | Track acknowledgement/delivery; unknown result -> reconcile |
| 10 Await response | Persist wait and due follow-up jobs | Reply -> correlate; reject/expiry/opt-out -> stop follow-ups |
| 11 Accept | Verify customer/version; revalidate ERP facts | Changed material terms -> new quote; duplicate -> existing result |
| 12 Commit order | Reserve if supported; create with stable external reference | Store ERP ID; partial/unknown result -> reconciliation |
| 13 Finish | Update business status; optional CRM synchronization | CRM failure is retried independently; never recreate successful ERP order |

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
If reservation succeeds but order creation fails conclusively, release or expire the reservation according to ERP policy.
If creation outcome is unknown, reconcile before releasing/retrying; do not cancel stock belonging to an order that actually exists.
Record compensating actions and unresolved exceptions for an operator.

## Workflow upgrades
Persist graph/schema version. Keep compatible handlers for waiting runs or provide tested migrations; never assume a deployment can resume old checkpoints safely.
