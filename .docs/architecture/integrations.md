# Integration contracts
Contracts below are design schemas, not implemented endpoints or classes.

## Channel adapters
A channel adapter verifies provider events and maps them into a common envelope:
```json
{
  "schema_version": 1,
  "event_id": "internal-uuid",
  "tenant_id": "resolved-server-side",
  "connection_id": "configured-channel-connection",
  "channel": "telegram",
  "provider_event_id": "provider-stable-id",
  "conversation_id": "provider-thread-or-chat",
  "sender_external_id": "provider-user-id",
  "occurred_at": "2026-10-22T10:00:00Z",
  "received_at": "2026-10-22T10:00:01Z",
  "text": "Please quote 50 industrial fans for Pune",
  "attachments": [],
  "reply_to_external_id": null,
  "correlation_id": "internal-correlation-id"
}
```
The tenant comes from a verified connection or authenticated API membership, never an untrusted tenant field.
Normalize message, edit, delivery, opt-out and callback event types separately. Provider duplicate key: tenant + connection + event type + provider event ID.
Business duplicates across different channels are candidates for review, not automatic deletion based on similar text.
Maintain identities per tenant/channel; link customers across channels only through verified evidence or authorized staff action.

Required operations: verify_event, normalize_event, send_message, upload_or_link_document, normalize_delivery_event.
Capabilities include attachments, buttons, threading, message limits and permitted outbound initiation. Unsupported capability is explicit.
Provider-specific reply windows, consent, template requirements and permissions are adapter policy inputs and must be verified at implementation.
Retries preserve operation identity. Delivery status distinguishes pending, provider_accepted, delivered, failed and unknown.

## ERP/inventory adapters
Required read operations:
- search_products(query, customer_context): SKU candidates with authoritative IDs, units and descriptions.
- get_prices(skus, customer, currency, effective_at): price list/version, effective dates, currency, units and discount basis.
- get_availability(skus, quantities, warehouse): on-hand/reserved/available semantics, source timestamp and availability confidence.
Optional write operations: reserve_stock, release_reservation, create_sales_order, get_order_by_external_reference.
Delivery promises require a supported business rule or delivery source; stock alone does not prove arrival by a requested date.

Results include source system, fetched_at, external version where available, and normalized errors:
not_found, unsupported, unauthenticated, forbidden, rate_limited, temporary_unavailable, invalid_request, conflict, unknown_outcome.
A tenant connector declares capabilities and whether external idempotency/reference lookup is supported.
If safe duplicate prevention/reconciliation is impossible, order creation requires a manual completion path instead of blind retry.

## Caching and mapping
Caches are tenant/connection scoped, timestamped and disposable. Staleness policy is configured per operation.
Normalize units, currency, customer-specific price lists, warehouses and tax identifiers through documented mappings.
AI cannot infer missing unit conversion, tax policy or inventory semantics.
ERP webhooks may invalidate caches; reads still revalidate material facts before order commitment.

## Planned API surface
Versioned /api/v1 routes: enquiries (create/status), quotations (read/version), approvals (decision), acceptances (submit), integrations (admin), and provider-specific webhook routes.
Create/decision APIs support idempotency keys; version conflicts return explicit conflict responses.
Webhook routes verify provider authentication; portal/API routes verify user or service identity and tenant membership.
Write OpenAPI examples and exact status codes alongside implementation; this list is not an existing API specification.
