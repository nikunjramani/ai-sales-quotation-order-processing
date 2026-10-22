# 0002: Tenant isolation from the foundation
Date: 2026-10-22
Status: accepted design; implementation pending

## Context
One installation may serve multiple independent businesses.

## Decision
Carry trusted tenant context across API, repositories, jobs, storage and workflow access. Use tenant-aware constraints and PostgreSQL RLS as defense in depth with non-owner runtime roles. Authorize checkpoint access through run mappings.

## Alternatives considered
Single-tenant prototype retrofit; separate database per business initially.

## Consequences
More initial schema/test work; pooled DB context and third-party checkpoint storage require deliberate enforcement. Dedicated tenant databases remain a future option.

## Verification
Two-tenant negative tests across records, callbacks, documents, checkpoints, approvals and integration secrets.
