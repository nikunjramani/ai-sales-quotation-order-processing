# Current handoff
Updated: 2026-10-22.

## Current state
Current milestone: M1 (domain and tenancy) is implemented and verified against local PostgreSQL. It is not yet committed or pushed, so the CI run for M1 is pending.
M0 foundation is COMPLETE: exit checks passed locally and in a fresh GitHub Actions run. Foundation commits c6d163c and c6c63dc are on origin/main.
Public [repository](https://github.com/nikunjramani/ai-sales-quotation-order-processing), branch main. The user's local .vscode/settings.json is intentionally untracked.
No HTTP business route, AI integration, real provider/ERP connection, approval/order feature or deployment exists.

## Implemented
- M0: uv-locked Python package, validated settings, local credential generator, FastAPI health endpoints, PostgreSQL Compose with owner/runtime roles, tenant table with forced RLS, synthetic seed, offline/integration tests and CI. See [setup](development/setup.md) and [configuration](development/configuration.md).
- M1, described in [quotation pricing](features/quotation-pricing.md), [ADR 0010](adr/0010-deterministic-pricing-and-tenant-context.md) and the [code map](development/code-map.md):
  - Decimal money with named rounding.
  - Roles, permissions and a membership-based `TenantContextResolver`.
  - ERP fact types and the `ErpReader` port with normalized `ErpError`.
  - The deterministic `calculate_quotation` (absent price never zero; five stock statuses).
  - The read-only `QuotationPricingService`, a per-tenant simulated ERP with demo catalogues, and SQL membership/policy repositories.
  - Migration 0002 (memberships and pricing policies, forced RLS, runtime SELECT only), extended seed, the demo script, and import-boundary tests.

## Decisions recorded
- ADR 0010: per-line rounding with the tenant's mode; one tenant tax rate on the subtotal; one currency; no unit conversion or discounts; stock never blocks calculation but is always reported; administrators do not approve unless also approvers.
- The ERP contract adds `get_products`; customer-specific pricing is deferred.
- These are synthetic defaults that the pilot business must validate.
- Earlier decisions still stand: ADR 0007 supersedes 0005; ADR 0008 defers negotiation; every negotiated revision needs manager approval; direct email reply approval is confirmed; manager commercial commands wait for M11 with no assumed global price-write authority. See the [ADR index](adr/README.md).

## Verification (M1, 2026-10-22)
- Ruff lint/format and mypy (strict, 47 files) pass.
- Offline pytest: 73 unit passed, 11 integration skipped. Tests were reorganized into tests/unit (mirrors src) and tests/integration with shared conftest fixtures; see [testing](development/testing.md).
- `scripts/check_database.py` on local PostgreSQL 17.11: upgrade to 0002, `alembic check` reported no drift, 84 passed.
- `alembic downgrade 0001_tenants` left only `tenants` and `alembic_version`. `downgrade base` -> `upgrade head` -> 84 passed again.
- psql confirmed RLS is enabled and forced on tenants, memberships and tenant_pricing_policies.
- Seed is idempotent.
- `scripts/demo_quotation.py`:
  - Valid INR quote: subtotal 9336.25, tax 1680.53, total 11016.78, cable stock unknown.
  - Blocked request: price_missing, quantity_not_multiple, product_not_found (another tenant's SKU).
  - Cross-tenant access denied; viewer drafting denied.
- The local DB container remains running with its named volume. No app server is running.
- Not yet run: GitHub Actions for M1 (needs push).
- Known CI warnings: actions/checkout@v4 and setup-python@v5 target deprecated Node 20; ubuntu-latest is migrating to Ubuntu 26.

## Next task
1. With user authorization, commit M1 and push to main. Confirm CI passes, then mark M1 complete in the roadmap, ADR 0010 and this handoff.
2. Then start M2 (intake): manual/API intake, canonical event schema, inbox dedupe, durable job worker, and private attachment storage/quarantine.
   - M2 needs an authenticated API boundary. Until OIDC (M4), decide with the user how API callers are authenticated in development, for example service tokens per tenant. Do not expose tenant data without authentication.
- Before M3 choose the model provider and budget. Before M5/M7 choose the email provider and pilot ERP.
- Update this handoff in every change; never mark milestones complete without evidence.
