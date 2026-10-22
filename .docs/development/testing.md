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

## AI evaluation dataset
Synthetic cases include aliases, misspellings, ambiguous SKUs, multiple items, missing quantities, conflicting dates, units, currencies, malicious instructions and unsupported attachment formats.
Track field extraction correctness, SKU match correctness, appropriate clarification, invented factual values, latency and cost.
Release blocking invariants: no model-origin price/stock accepted as authoritative; no tool authorization from model text; no bypass of approval/tenant checks.
Set measured extraction/latency targets before pilot; do not invent passing scores in advance.
Keep prompt/model/version and dataset version with results. Use deterministic stubs for routine tests and opt-in bounded live model evaluations.
A test that mirrors implementation without asserting business behaviour is insufficient.
