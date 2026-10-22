# Code map
Status: only the M0 foundation below exists. The later module map remains a plan.

## Implemented foundation
| Actual file | Responsibility |
|---|---|
| [pyproject.toml](../../pyproject.toml) / [uv.lock](../../uv.lock) | Package configuration, quality checks and reproducible dependencies |
| [config.py](../../src/quotation_app/config.py) | Environment/.env validation and secret wrappers |
| [app.py](../../src/quotation_app/api/app.py) | Application factory, lifecycle and health routes |
| [database.py](../../src/quotation_app/persistence/database.py) | Bounded connection pool and schema/runtime-role readiness |
| [models.py](../../src/quotation_app/persistence/models.py) | Initial Tenant registry metadata |
| [0001_tenants.py](../../migrations/versions/0001_tenants.py) | Initial schema, forced RLS and runtime read grants |
| [env.py](../../migrations/env.py) | Alembic execution with separate owner credentials |
| [seed.py](../../src/quotation_app/persistence/seed.py) | Idempotent development/test-only fictional tenant fixtures |
| [compose.yaml](../../compose.yaml) / [init.sql](../../infra/postgres/init.sql) | Local database container, persistent volume and role bootstrap |
| [init_local_env.py](../../scripts/init_local_env.py) | Generate ignored local credentials without overwriting |
| [check_database.py](../../scripts/check_database.py) | Run local migration/schema/integration checks |
| [test_config.py](../../tests/test_config.py) / [test_health.py](../../tests/test_health.py) | Offline configuration/API behaviour |
| [test_database.py](../../tests/integration/test_database.py) | Opt-in PostgreSQL role, seed and RLS checks |
| [ci.yml](../../.github/workflows/ci.yml) | Automated offline and live PostgreSQL checks; passing on main |

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
