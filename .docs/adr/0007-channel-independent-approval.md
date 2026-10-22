# 0007: Channel-independent manager approval
Date: 2026-10-22
Status: accepted design; implementation pending
Supersedes: [0005](0005-versioned-approval.md)

## Context
Managers must be able to review and decide from configured messaging channels on mobile without opening the portal for every quotation. The portal remains available. Adding a provider should not change quotation or order rules.

## Decision
Introduce a channel-independent approval application service. Portal requests and verified channel interactions map into the same decision command. The service owns authorization, immutable quote-version binding, concurrency, audit and durable workflow resume. Transport adapters only render review packets and translate verified interactions.
Each tenant configures manager identities and permitted approval channels independently of customer enquiry channels. A customer messaging identity is not an internal manager identity.
Support in-channel review and approve/reject/request-revision where the provider and configured authentication permit it. User clarification on 2026-10-22 confirms direct email reply approval. Verify sender identity and exact task/version correlation; do not infer authorization from quoted, ambiguous or automatic reply text. The portal remains optional for routine verified decisions.

## Alternatives
Require portal use for every decision; duplicate approval business rules per channel; allow arbitrary free-text approval without verified identity and task/version correlation.

## Consequences
Identity enrollment, revocation, callback verification and capability tests are required. Provider-specific approval support is distinct from general messaging support. Portal fallback must be explicit if a channel cannot provide sufficient review/authentication. Financial authorization remains deterministic and version-bound.
One codebase can contain independently testable modules; this decision does not require separate microservices.

## Verification
Run shared approval tests through portal and simulated channel adapters; demonstrate a real messaging adapter before claiming mobile in-channel approval. Reject stale buttons, forwarded actions, unauthorized users, revoked bindings and cross-tenant callbacks. Concurrent portal/chat decisions produce one authoritative result.
