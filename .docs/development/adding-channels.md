# Adding a channel (email, Telegram, WhatsApp...)
**Status:** the extension points below are implemented (M4/M5). The working examples are the API pull delivery and the simulated manager channel. No real provider is connected yet; email was deferred by the user on 2026-10-23 ([ADR 0015](../adr/0015-quotation-documents-and-delivery.md)).

A "channel" plays up to three roles. Each role is a small adapter; the business rules (approval, delivery outcomes, idempotency, tenant checks) stay in the application layer and do not change.

| Role | Port | Example today | Where it is registered |
|---|---|---|---|
| Customer enquiries in | Intake envelope ([domain/intake.py](../../src/quotation_app/domain/intake.py)) | API (`POST /api/v1/enquiries`) | its own API route |
| Quotation PDF out to the customer | `DeliveryChannel` ([ports/documents.py](../../src/quotation_app/ports/documents.py)) | [adapters/delivery/api.py](../../src/quotation_app/adapters/delivery/api.py) | channel map in [worker.py](../../src/quotation_app/worker.py) |
| Manager review and approval | `ApprovalNotifier` ([ports/channels.py](../../src/quotation_app/ports/channels.py)) + inbound route | [adapters/channels/simulated.py](../../src/quotation_app/adapters/channels/simulated.py) + [api/channels.py](../../src/quotation_app/api/channels.py) | notifier map in [worker.py](../../src/quotation_app/worker.py); route in [api/app.py](../../src/quotation_app/api/app.py) |

## A. Sending approved quotations through a new channel
1. **Intake first.** Enquiries from the channel must be stored with that channel's name in `Channel` and with the **provider-verified sender** as `sender_external_id` (e.g. the authenticated From address). [`delivery_recipient`](../../src/quotation_app/domain/documents.py) sends the quotation back to exactly that sender. It never uses an address found in the message text.
2. **Write the adapter**, e.g. `adapters/delivery/email.py`:
   ```python
   class EmailDelivery:
       channel = "email"

       def deliver(self, request: DeliveryRequest, document: bytes) -> DeliveryReceipt:
           # Send `document` as request.filename to request.recipient.
           # Use request.delivery_id as the provider idempotency key / Message-ID.
           return DeliveryReceipt(ReceiptKind.SENT, provider_message_id)
   ```
   Map provider outcomes to the contract:
   - The provider accepted it: return `SENT` with its message ID.
   - A permanent refusal (bad address, blocked, too large): raise `DeliveryRejected`. The delivery becomes `failed`.
   - The request may have reached the provider (a timeout after sending): raise `DeliveryUncertain`. It becomes `unknown` and is **never resent automatically**.
   - Anything else means nothing was handed over. It is retried with backoff, and the last attempt records `failed`.
3. **Register it** in the worker's channel map. Add credentials as `SecretStr` settings in [config.py](../../src/quotation_app/config.py). Refuse sandbox/dev settings in production, like `simulated_channel_secret`.
4. **Test it:**
   - Unit-test the outcome mapping with a fake provider; [`RecordingDeliveryChannel`](../../tests/unit/conftest.py) shows the expectations.
   - Add a sandbox integration test that runs only when the sandbox credentials are set.
5. **Document it:** the configuration reference, the feature document and the handoff.

## A2. Customer answers through a new channel (M6)
Today customers accept or decline through the API only. Another channel (an acceptance link, an email reply) needs:
- an inbound route that verifies the customer (an open decision for each channel);
- the call `QuotationResponseService.respond(context, enquiry_id, channel, key, request)`, with the exact version and hash.

All acceptance rules (validity, price re-check, one closing answer, replays) already live in that service. Ask the user about each channel's verification before building it.

## B. Manager approval through a new channel (e.g. email reply)
Resolve the open decision "Direct email approval verification" first. It decides what counts as trusted inbound evidence (provider signature, SPF/DKIM/DMARC results) and how a reply is tied to one task and version.
1. Add the channel to `ApprovalChannel` in [domain/quotations.py](../../src/quotation_app/domain/quotations.py). The portal's "link an account" (enrollment) then accepts it automatically.
2. **Outbound:** write an `ApprovalNotifier` (`send_review(binding, packet, action_reference, expires_at)`).
   - Use `render_template(TemplateKey.APPROVAL_REQUEST, {"packet": packet}).text` (domain/messages.py) for the body.
   - Carry the opaque `action_reference` where the reply brings it back (e.g. a per-task reply address or token). Never put the tenant or task ID in a form a person could edit and have trusted.
   - Register it in the worker's `notifiers` map.
3. **Inbound:** add a route next to the simulated one in [api/channels.py](../../src/quotation_app/api/channels.py).
   - Verify the provider signature on the raw body **before** parsing.
   - Reject automatic replies (`Auto-Submitted`, bounces), and text quoted from the original message.
   - Translate the event into a `ChannelEvent` (enroll or decision, with the verified sender as `external_user_id`) and call `ChannelActionService.handle`.
   - That service and `ApprovalService` already enforce the rest: enrolled account, single-use 24-hour reference bound to one task and account, current version and content hash, approver role, no self-approval, one decision per task, and replay safety.
4. **Test it** with the cases from the roadmap:
   - spoofed sender;
   - forwarded message (another account);
   - quoted or automatic reply;
   - stale version;
   - reused reference.

   The unit tests in [test_channel_actions.py](../../tests/unit/application/test_channel_actions.py) show the shape.

## What you never need to change
- `ApprovalService`, `ChannelActionService` and `QuotationDeliveryHandler`.
- The workflow graph and the database tables.
- The portal: decisions, delivery status and linked accounts already show any channel by name.

New tables are needed only if the provider has state of its own (e.g. a mailbox cursor).
