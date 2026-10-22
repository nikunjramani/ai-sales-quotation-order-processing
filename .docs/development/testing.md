# Testing and AI evaluation
## Required suites
- Domain unit tests: Decimal totals, rounding, quantity/unit validation, expiry, pricing policies, missing values.
- PostgreSQL integration tests: real migrations, tenant policies, unique constraints, transactional inbox/outbox, job leases.
- Adapter contracts: every ERP/channel implementation passes shared fixtures; provider sandbox tests validate actual APIs.
- Workflow tests: clarification, rejection, revision, restart/resume, provider failures, model failures, expiry and accepted order.
- Security tests: cross-tenant reads/writes/downloads/checkpoints, forged webhooks, stale approvals, role bypass and attachment handling.
- Concurrency/recovery: simultaneous approvals/acceptances, repeated jobs, worker crash, graph replay, timeout after remote success.
- End-to-end: two tenants and two channels through approved PDF and sandbox ERP order.
- Release tests: backup restore, migration/rollback strategy, deployment smoke tests and documented load profile.

## Additional approval and extension coverage
- Run the same approval contract cases through portal, fake channel and each supported real channel adapter.
- Verify enrolled actor/tenant/context, forwarded actions, revoked roles, expired/stale buttons and conflicting portal/chat decisions.
- Verify full quote review detail is accessible in-channel and provider limitations produce explicit fallback rather than silent approval.
- Confirm notifications across channels reference one task; retries or failed confirmations never duplicate decisions/resumes.
- Add import-boundary checks when modules exist; a new approval provider must not require financial-domain or graph-routing edits.
- Deferred negotiation tests are defined in the [negotiation plan](../plan/negotiation.md); no feature pass is claimed before implementation.
- Direct email decisions must exclude quoted approvals, automatic replies and ambiguous/conditional text, and verify sender plus exact task/version.
- Deferred manager commands must distinguish read-only stock questions from scoped changes, reject ambiguous global price writes and require approval of every negotiated revision, even if the proposed discount is within policy limits.

## Lifecycle and ingestion coverage
- Unsupported, encrypted, oversized and scanned PDFs must not silently produce empty successful requirements. Preserve extraction evidence and route to clarification/review where unsupported.
- Draft previews and final PDFs must match the exact reviewed quotation values/version; previews cannot be dispatched as approved offers.
- Test human pause versus dispatch, authorized resume, cancellation versus order commitment, expired/withdrawn offers and acceptance across multiple revisions of one purchase.
- Order confirmation requires confirmed ERP success; failed confirmation retries must never create another order.

## AI evaluation dataset
Synthetic cases include aliases, misspellings, ambiguous SKUs, multiple items, missing quantities, conflicting dates, units, currencies, malicious instructions and unsupported attachment formats.
Track field extraction correctness, SKU match correctness, appropriate clarification, invented factual values, latency and cost.
Release blocking invariants: no model-origin price/stock accepted as authoritative; no tool authorization from model text; no bypass of approval/tenant checks.
Set measured extraction/latency targets before pilot; do not invent passing scores in advance.
Keep prompt/model/version and dataset version with results. Use deterministic stubs for routine tests and opt-in bounded live model evaluations.
A test that mirrors implementation without asserting business behaviour is insufficient.
