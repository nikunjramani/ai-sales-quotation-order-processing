# Connections (phase 1)
Decision: [ADR 0018](../adr/0018-connector-framework.md). Plan: [phase 1](../plan/platform/implementation/phase-1-foundations.md). Adding a tool: [adding providers](../development/adding-providers.md).

## What it does
Each business's tools are **connections**. A connection is one use of a **provider**, the tool package (`api`, `simulated`; later Telegram, email, ERPs). The core decides by what a connection is for (its purposes) and what its provider can do (capabilities), never by the provider's name.

| Today | Connection | Purposes |
|---|---|---|
| Each API key | `api`, account `api-key:<id>` (created and disabled together with the key) | customer messages (pull) |
| The demo businesses' simulated phone and demo catalogue | `simulated`, account `simulated-local` (seed) | manager approvals, product data |

## Flows
- **Inbound** (`POST /api/v1/hooks/{connection_id}/{webhook_token}`):
  1. The token is checked against its stored SHA-256.
  2. The provider verifies the signature on the raw body.
  3. The provider parses events. The business is always the connection's.
  4. Each event is stored once, with a `process_inbound` job. The job routes manager actions through the same approval core as the portal and records the outcome (`enrolled`, `recorded`, `replayed`, `rejected`, `conflict`).
- **Outbound:** quotations, approval requests and notices are rows in `outbound_messages`, sent by the `send_message` job:
  - The status is honest: `unknown` is never resent.
  - The single-use approval token is created only at send time.
  - Each quotation delivery mirrors its message's status.
- **Product data:** each business's active catalogue connection is its product source. With none, an enquiry goes to review with "No product source is connected".

## Portal
**Connections** (`#/connections`; `#/channels` redirects there):
- Administrators see every tool, with its last error.
- Approvers see the tools they can link and "Link my account on <tool>". The one-time code works only on that tool.
- Linked accounts show the tool's name.

## Development
- **Signing and tokens:** `QUOTATION_SIMULATED_CHANNEL_SECRET` (development) signs the deprecated `/api/v1/channels/simulated/events` route. Through the seed, it is also the demo phone's signing secret, stored in the local secret store. The demo phone's webhook token is derived from it.
- **Tools:** `scripts/simulated_channel.py --via hooks` uses the generic route; the demo page uses the old one.
- **Secret store:** `QUOTATION_SECRET_STORE_KEY` encrypts the local secret store. `init_local_env.py --add-missing` creates it.

## Security
See [security](../operations/security.md#implemented-controls-phase-1-connector-framework-in-progress).

## Not yet
Enabling tools from the portal and real providers (phase 5); customer messages and website chat (phase 4).
