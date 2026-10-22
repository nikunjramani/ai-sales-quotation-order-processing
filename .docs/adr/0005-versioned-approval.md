# 0005: Version-bound internal approval and customer acceptance
Date: 2026-10-22
Status: accepted design; implementation pending

## Context
Notifications, commercial authorization and customer purchase acceptance are different actions.

## Decision
All initial-release quotes require authenticated internal review of an immutable version. Notifications open portal review; only authorized state-changing requests decide. Customer acceptance is recorded separately and triggers revalidation.

## Alternatives considered
Approve directly from unauthenticated email links; interpret any chat yes as authorization; approve mutable quote objects.

## Consequences
Additional portal/identity work; stale approvals and expired acceptance must fail. Material revisions need fresh approval and customer acceptance where applicable.

## Verification
Role, tenant, expiry, CSRF, version change, replay and concurrent decision tests.
