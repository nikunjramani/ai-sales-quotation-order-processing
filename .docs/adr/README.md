# Architecture decision records
Accepted denotes intended design, not implemented code. Date: 2026-10-22.

- [0001: Channel-independent core and adapters](0001-adapter-boundaries.md) — accepted
- [0002: Tenant isolation from the foundation](0002-tenant-isolation.md) — accepted
- [0003: Existing ERP remains authoritative](0003-erp-authority.md) — accepted
- [0004: Persisted graph with durable jobs and outbox](0004-durable-execution.md) — accepted
- [0005: Version-bound internal approval and customer acceptance](0005-versioned-approval.md) — superseded by 0007
- [0006: Versioned documentation and portable agent instructions](0006-portable-documentation.md) — accepted
- [0007: Channel-independent manager approval](0007-channel-independent-approval.md) — accepted; core implemented in M4 (portal + simulated channel, ADR 0013); real providers M5/M7
- [0008: Deferred negotiation module](0008-negotiation-extension.md) — accepted; manager approval mandatory; implementation deferred
- [0009: Foundation tooling and database roles](0009-foundation-tooling.md) — implemented and verified (local and CI)
- [0010: Deterministic pricing and trusted tenant context](0010-deterministic-pricing-and-tenant-context.md) — implemented in M1; verified locally and in CI
- [0011: Durable intake, PostgreSQL job queue, attachment quarantine and API keys](0011-durable-intake-and-jobs.md) — implemented in M2; verified locally and in CI
- [0012: Provider-independent enquiry extraction with LangGraph and verbatim checks](0012-provider-independent-extraction.md) — implemented in M3; verified locally and in CI
- [0013: Portal identity, immutable versions and the shared approval core](0013-portal-identity-and-approval-core.md) — implemented in M4; verified locally
- [0014: Portal structure by feature and layer, with TanStack Query and Zustand](0014-portal-structure-and-state.md) — implemented; verified locally

New decisions get sequential IDs. Preserve history and explicitly link superseding records.
