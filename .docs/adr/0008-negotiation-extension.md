# 0008: Deferred negotiation module
Date: 2026-10-22
Status: accepted design; implementation deferred

## Context
After receiving a quotation, the purchasing customer may request a lower price or different terms. The user wants this planned now and implemented after learning the core system.

## Decision
Plan negotiation as a later module that consumes a customer counteroffer tied to an existing quotation and requests a new draft through existing quotation services. It reuses pricing validation, approval, delivery and order acceptance instead of duplicating those rules.
Do not implement negotiation now. Initial-release negotiation requests route to human review without being treated as acceptance or automatic price changes.
User clarification on 2026-10-22: every negotiated revision requires manager approval. AI may interpret a request, retrieve facts and prepare proposals, but cannot negotiate autonomously or send unapproved revised commercial terms, even within configured limits.
The same later milestone includes manager stock enquiries and requests to change prices or add discounts through email, WhatsApp and other supported channels. These use shared business services and identity/authorization checks; see the manager-operations plan.

## Alternatives
Ignore counteroffers; treat them as a new unrelated enquiry; embed negotiation in every messaging adapter; enable autonomous negotiation immediately.

## Consequences
Versioning and response classification must preserve extension points. Detailed commercial policy, limits, expiry and race handling are prerequisites to implementation. Existing approval invariants remain in effect until explicitly revised by a later approved ADR.

## Verification
Before enabling the module, test discount boundaries, unknown costs, unsupported terms, customer/quote correlation, old-version acceptance, duplicate counteroffers, approval invalidation and negotiation/order races. Confirm negotiated totals always come from deterministic rules.
