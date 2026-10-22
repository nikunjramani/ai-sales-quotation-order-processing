# 0001: Channel-independent core and adapters
Date: 2026-10-22
Status: accepted design; implementation pending

## Context
Requests must arrive from several channels and serve different businesses.

## Decision
Use a canonical event envelope, channel ports and ERP ports. Provider payloads stay in adapters. Begin with a modular monolith; add providers without changing commercial domain rules.

## Alternatives considered
Email-specific workflow; separate complete application per provider; immediate microservices.

## Consequences
Provider differences remain explicit capabilities. Every adapter needs mapping, authentication and shared contract tests.

## Verification
Process equivalent email/Telegram fixtures through the same workflow; verify unsupported capabilities fail explicitly.
