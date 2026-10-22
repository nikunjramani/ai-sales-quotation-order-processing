# 0004: Persisted graph with durable jobs and outbox
Date: 2026-10-22
Status: accepted; partially implemented (M2: inbox dedupe, atomic receipt plus job, leased/fenced PostgreSQL job queue with backoff - see ADR 0011). Outbox, scheduler and LangGraph checkpoints pending.

## Context
Workflows wait days, workers crash and remote calls have uncertain outcomes.

## Decision
Use LangChain for bounded model interactions, LangGraph with PostgreSQL checkpoints for workflow control, and PostgreSQL inbox/jobs/outbox for durable execution intents. Separate worker/dispatcher roles. Keep n8n optional and peripheral.

## Alternatives considered
In-memory waits; FastAPI background tasks as durable queue; n8n as parallel business workflow authority; Redis broker immediately.

## Consequences
At-least-once execution requires idempotency and reconciliation. Checkpoint and business transactions are not assumed atomic. Lease scheduling is a real implementation obligation.

## Verification
Crash/restart, node replay, approval-resume race, delayed-job and remote-timeout tests.
