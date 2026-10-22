# Proposed code map
Status: these application directories do not exist yet. Create only as milestones require.

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
