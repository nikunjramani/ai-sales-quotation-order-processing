# Adding a provider (a tool: email, Telegram, WhatsApp, an ERP...)
**Status:** the framework is implemented (phase 1, [ADR 0018](../adr/0018-connector-framework.md)). The working examples are [`api`](../../src/quotation_app/adapters/providers/api/__init__.py) and [`simulated`](../../src/quotation_app/adapters/providers/simulated/provider.py). Real providers and the portal's "Enable" button come in phase 5.

A provider is one package. It never changes the API, the worker, the application services, the database or the portal. The core asks what a connection is **for** (its purposes) and what its provider **can do** (capabilities), never which provider it is. An architecture test enforces this.

## Words
| Word | Meaning |
|---|---|
| Provider | The tool package, e.g. `telegram`. One per tool, shared by all businesses |
| Connection | One business's use of a provider: a row in `connections` with purposes, settings, secret **references** and status |
| Purpose | What the connection is used for: `customer_messages`, `manager_approvals`, `catalogue` |
| Capabilities | What the provider can do: push or pull delivery, webhooks, buttons, attachments, limits |

## Steps
1. **Create the package** `src/quotation_app/adapters/providers/<key>/` (or a separate installable package). Provider SDKs are imported only here. Add each new third-party package to the adapters allow-list in [test_architecture.py](../../tests/unit/test_architecture.py); every version must be at least 14 days old.
2. **Implement `Provider`** ([ports/providers.py](../../src/quotation_app/ports/providers.py)):
   - `key`, `display_name`, `purposes`, `capabilities`, and `dev_only` (true means the provider is skipped in production).
   - `verify_inbound(conn, secrets, request)`: check the signature or token on the **raw bytes** and raise `InboundRejected`. It runs before parsing.
   - `parse_inbound(conn, request)`: return normalised events (`CustomerMessage`, `ManagerAction`, `DeliveryStatusUpdate`, `ConsentChange`), each with a stable `provider_event_id`. Never read a business or tenant from the body: the business is always the connection's. Raise `InvalidInbound` for content you cannot understand.
   - `send(conn, secrets, message)`:
     - Return `SendReceipt(SENT or AVAILABLE, provider_message_id)`. The ID must be **unique per message**.
     - Raise `SendRejected` for a permanent refusal.
     - Raise `SendUncertain` when the message may have been accepted; it is never resent.
     - Any other error means nothing was handed over, and the message is retried.
   - `catalogue_reader(conn, secrets)`: only for `Purpose.CATALOGUE`; it returns an `ErpReader`.
   - `test(conn, secrets)`: a quick check of the connection.
   - Anything the provider does not support raises `OperationUnsupported`, never a fake success.
3. **Secrets:** read them only through `secrets.get(conn.tenant_id, conn.secret_refs[name])`. Never store them in `config`, log them or put them in errors.
4. **Register the factory** in `pyproject.toml`, then run `uv sync`:
   ```toml
   [project.entry-points."quotation_app.providers"]
   telegram = "quotation_app.adapters.providers.telegram:build"
   ```
   `build(environment: ProviderEnvironment) -> Provider`. The provider's key must equal the entry point name.
5. **Add a contract sample** in [test_provider_contract.py](../../tests/unit/providers/test_provider_contract.py): a body the provider accepts and how to sign it. A test fails until the sample exists. Catalogue providers also run the [ERP contract suite](../../tests/unit/ports/test_erp_contract.py).
6. **Sandbox test:** an integration test that runs only when sandbox credentials are set.
7. **Document:** the configuration reference (if the provider adds company-level settings, they are generic and never provider-named), a feature note, and the handoff.

## What happens without any core change
- **Inbound:** callbacks arrive on `POST /api/v1/hooks/{connection_id}/{webhook_token}`. They are verified, stored once and routed by event type: manager actions go to the same approval core the portal uses.
- **Outbound:** quotations, approval requests and notices are queued in the outbox and sent by `send_message`. The approval token is added at send time; the PDF is attached and hash-checked.
- **Product data:** a business's catalogue connection becomes its product source for matching, pricing and acceptance.
- **Portal:** the Connections page lists the new tool, and approvers can link an account on it.

## Not yet (phase 5)
Self-service Enable/Disable (`provision`, `resume`), GET webhook handshakes, platform-wide webhooks (one URL per app) and sending questions to customers. See the [phase 5 plan](../plan/platform/implementation/phase-5-one-click-providers.md).
