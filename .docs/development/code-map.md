# Code map
Status: the M0 foundation and M1 domain/tenancy modules below exist. The remaining module map is a plan.

## Implemented foundation
| Actual file | Responsibility |
|---|---|
| [pyproject.toml](../../pyproject.toml) / [uv.lock](../../uv.lock) | Package configuration, quality checks and reproducible dependencies |
| [config.py](../../src/quotation_app/config.py) | Environment/.env validation and secret wrappers |
| [app.py](../../src/quotation_app/api/app.py) | Application factory, lifecycle and health routes |
| [database.py](../../src/quotation_app/persistence/database.py) | Bounded connection pool and schema/runtime-role readiness |
| [models.py](../../src/quotation_app/persistence/models.py) | Tenant, Membership and TenantPricingPolicy table metadata |
| [0001_tenants.py](../../migrations/versions/0001_tenants.py) | Initial schema, forced RLS and runtime read grants |
| [env.py](../../migrations/env.py) | Alembic execution with separate owner credentials |
| [seed.py](../../src/quotation_app/persistence/seed.py) | Idempotent development/test-only fictional tenants, memberships and policies |
| [compose.yaml](../../compose.yaml) / [init.sql](../../infra/postgres/init.sql) | Local database container, persistent volume and role bootstrap |
| [init_local_env.py](../../scripts/init_local_env.py) | Generate ignored local credentials without overwriting |
| [check_database.py](../../scripts/check_database.py) | Run local migration/schema/integration checks |
| [tests/](../../tests/conftest.py) | `unit/` mirrors `src/quotation_app`; `integration/` needs PostgreSQL; shared fixtures in conftest files. See [testing](testing.md) |
| [ci.yml](../../.github/workflows/ci.yml) | Automated offline and live PostgreSQL checks; passing on main |

## Implemented M1 domain and tenancy
Dependency direction: application -> ports -> domain; adapters and persistence implement ports. [test_architecture.py](../../tests/unit/test_architecture.py) enforces the domain/ports/application/adapters import rules.

| Actual file | Responsibility |
|---|---|
| [domain/money.py](../../src/quotation_app/domain/money.py) | Decimal Money, currency codes, rounding modes, exact multiplication |
| [domain/tenancy.py](../../src/quotation_app/domain/tenancy.py) | Roles, permissions, TenantContext, authorization errors |
| [domain/catalogue.py](../../src/quotation_app/domain/catalogue.py) | ERP fact values: Product, PriceQuote, StockLevel |
| [domain/pricing.py](../../src/quotation_app/domain/pricing.py) | PricingPolicy and the deterministic `calculate_quotation` rules |
| [ports/erp.py](../../src/quotation_app/ports/erp.py) | ErpReader protocol and normalized ErpError codes |
| [ports/tenancy.py](../../src/quotation_app/ports/tenancy.py) | Membership and pricing-policy reader contracts |
| [application/tenancy.py](../../src/quotation_app/application/tenancy.py) | TenantContextResolver: subject + stored membership -> context |
| [application/pricing.py](../../src/quotation_app/application/pricing.py) | QuotationPricingService use case (read-only) |
| [adapters/erp/simulated.py](../../src/quotation_app/adapters/erp/simulated.py) | Per-tenant in-memory ERP, failure injection, synthetic demo catalogues |
| [persistence/tenancy.py](../../src/quotation_app/persistence/tenancy.py) | `tenant_transaction` and SQL membership/policy readers |
| [0002_memberships_policies.py](../../migrations/versions/0002_memberships_policies.py) | Membership and pricing-policy tables, forced RLS, runtime SELECT grants |
| [demo_quotation.py](../../scripts/demo_quotation.py) | Prints a pricing trace and access-denial examples |
| [tests/unit/domain/](../../tests/unit/domain/test_pricing.py) | Rule tests: rounding, quantities, units, prices, stock, roles |
| [tests/unit/application/](../../tests/unit/application/test_pricing.py) / [test_erp_contract.py](../../tests/unit/ports/test_erp_contract.py) | Use-case behaviour and the shared ERP adapter contract suite |
| [tests/integration/persistence/test_tenancy.py](../../tests/integration/persistence/test_tenancy.py) | Two-tenant negative tests through the PostgreSQL runtime role |

## Planned modules

| Proposed location | Responsibility |
|---|---|
| src/quotation_app/api/ | HTTP routes, auth dependency and webhook handling |
| src/quotation_app/domain/ | Business models, money, pricing and policy rules |
| src/quotation_app/application/ | Use cases, transaction boundaries and authorization |
| src/quotation_app/application/approvals/ | Common review/decision service used by portal and manager channel adapters |
| src/quotation_app/application/negotiation/ (later) | Counteroffer lifecycle reusing existing quotation/approval services; deferred |
| src/quotation_app/application/manager_commands/ (later) | Verified stock enquiries and scoped change requests through existing services; deferred |
| src/quotation_app/workflows/ | LangGraph state, nodes, routing and versioning |
| src/quotation_app/ports/ | Typed interfaces for channels, ERP, model and storage |
| src/quotation_app/adapters/ | Provider-specific implementations and simulated ERP |
| src/quotation_app/persistence/ | Repositories, tables, tenant context and checkpoint access |
| src/quotation_app/workers/ | Jobs, scheduler, outbox and reconciliation |
| src/quotation_app/web/ | Portal templates and static assets |
| src/quotation_app/observability/ | Logging, tracing and metrics configuration |
| migrations/ | Alembic migrations and data transition notes |
| tests/ | Unit, integration, contract, security, workflow and evaluation suites |
| infra/ | Local Compose and deployment configuration |
| examples/ | Synthetic requests and provider examples |

Domain code must not import FastAPI routes, provider SDKs or graph orchestration.
Adapters implement ports. Workflow/application services depend on ports and domain rules.
See [module boundaries](../architecture/module-boundaries.md) for the expected change footprint of a new provider. Do not create the deferred negotiation module during foundation work.
When implemented, replace proposed descriptions with links to real paths/symbols, entry commands, and actual dependency flow.
No run/setup command is documented as working until it has been executed successfully.
