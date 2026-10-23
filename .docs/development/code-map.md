# Code map
Status: the M0 foundation, M1 domain/tenancy, M2 intake/jobs, M3 extraction, M4 approval/portal, M5 documents/delivery and M6 customer acceptance modules below exist. The remaining module map is a plan.

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

## Implemented M2 intake, jobs and attachments
Entry points: the HTTP API ([api/app.py](../../src/quotation_app/api/app.py)) and the worker process ([worker.py](../../src/quotation_app/worker.py)). Both are composition roots that wire adapters to application services. See [enquiry intake](../features/enquiry-intake.md).

| Actual file | Responsibility |
|---|---|
| [domain/intake.py](../../src/quotation_app/domain/intake.py) | Submission limits, payload fingerprint, idempotency-key rules, canonical InboundEnvelope |
| [domain/attachments.py](../../src/quotation_app/domain/attachments.py) | Storage keys, attachment statuses, content inspection |
| [domain/jobs.py](../../src/quotation_app/domain/jobs.py) | Job states, kinds, PermanentJobError, backoff with jitter |
| [ports/intake.py](../../src/quotation_app/ports/intake.py), [ports/jobs.py](../../src/quotation_app/ports/jobs.py), [ports/storage.py](../../src/quotation_app/ports/storage.py), [ports/api_keys.py](../../src/quotation_app/ports/api_keys.py) | Contracts for receipt storage, job queue, object storage and key lookup |
| [application/intake.py](../../src/quotation_app/application/intake.py) | EnquiryIntakeService: replay/conflict handling, quarantine writes, cleanup on failure |
| [application/api_keys.py](../../src/quotation_app/application/api_keys.py) | Key generation, token parsing, constant-time authentication |
| [application/preparation.py](../../src/quotation_app/application/preparation.py) | Idempotent attachment inspection job handler |
| [application/jobs.py](../../src/quotation_app/application/jobs.py) | JobRunner: complete, retry with backoff, dead-letter, lease-loss tolerance |
| [api/enquiries.py](../../src/quotation_app/api/enquiries.py) | `/api/v1/enquiries` routes, bearer auth, size limit, error mapping |
| [worker.py](../../src/quotation_app/worker.py) | `python -m quotation_app.worker [--once]` |
| [persistence/intake.py](../../src/quotation_app/persistence/intake.py) | Atomic receipt (inbox + enquiry + attachments + job), status reads, worker updates |
| [persistence/jobs.py](../../src/quotation_app/persistence/jobs.py) | SKIP LOCKED claims, leases, fenced completion |
| [persistence/api_keys.py](../../src/quotation_app/persistence/api_keys.py) | Key lookup via the narrow RLS policy; owner-only create/revoke |
| [adapters/storage/local.py](../../src/quotation_app/adapters/storage/local.py) | Local disk storage with strict keys and atomic writes |
| [0003_intake.py](../../migrations/versions/0003_intake.py) | Intake/job tables, composite tenant FKs, RLS, worker/API grants |
| [create_api_key.py](../../scripts/create_api_key.py) | Create (token shown once) or revoke API keys |
| [tests/unit/application/](../../tests/unit/application/test_intake.py), [tests/unit/api/test_enquiries.py](../../tests/unit/api/test_enquiries.py) | Use-case and HTTP contract tests over in-memory fakes |
| [tests/integration/api/test_enquiries.py](../../tests/integration/api/test_enquiries.py), [test_jobs.py](../../tests/integration/persistence/test_jobs.py) | End-to-end intake, races, durability, crash recovery and role isolation on PostgreSQL |

## Implemented M3 extraction workflow
Entry point: `extract_requirements` jobs in the worker ([worker.py](../../src/quotation_app/worker.py)). See [enquiry extraction](../features/enquiry-extraction.md). Import rules: `workflows` may use domain, ports, application, `langgraph` and `langchain_core`; provider SDKs stay in `adapters`.

| Actual file | Responsibility |
|---|---|
| [domain/requirements.py](../../src/quotation_app/domain/requirements.py) | RequestedItem, verbatim checks, unit aliases, decide_match, assess and template questions |
| [ports/interpretation.py](../../src/quotation_app/ports/interpretation.py) | EnquiryInterpreter (the swap point for models), DocumentReader, DocumentText |
| [ports/workflow.py](../../src/quotation_app/ports/workflow.py) | WorkflowStore: enquiry content, run/thread mapping, outcome recording |
| [workflows/enquiry.py](../../src/quotation_app/workflows/enquiry.py) | LangGraph graph (extract -> match -> assess -> ready/clarify/review) and ExtractionJobHandler |
| [adapters/interpreters/rules.py](../../src/quotation_app/adapters/interpreters/rules.py) | Free offline rules interpreter (default) |
| [adapters/interpreters/langchain.py](../../src/quotation_app/adapters/interpreters/langchain.py) | Any LangChain chat model: JSON + strict Pydantic, data-tagged prompts |
| [adapters/interpreters/factory.py](../../src/quotation_app/adapters/interpreters/factory.py) | Generic interpreter selection: no model = rules; `<provider>:<model>` = any LangChain chat model via `init_chat_model` (ADR 0017) |
| [adapters/documents/text.py](../../src/quotation_app/adapters/documents/text.py) | Bounded PDF/text reading; unsupported reasons instead of empty text |
| [persistence/workflow.py](../../src/quotation_app/persistence/workflow.py) | SqlWorkflowStore and the worker-role PostgreSQL checkpointer |
| [0004_workflow.py](../../migrations/versions/0004_workflow.py) | workflow_runs, frozen LangGraph checkpoint tables, M3 enquiry statuses, worker grants |
| [evaluation.py](../../src/quotation_app/evaluation.py) / [evaluate_extraction.py](../../scripts/evaluate_extraction.py) / [dataset](../../evals/enquiry_extraction.jsonl) | Provider evaluation through the real graph |
| [tests/unit/workflows/test_enquiry.py](../../tests/unit/workflows/test_enquiry.py), [tests/integration/workflows/test_enquiry.py](../../tests/integration/workflows/test_enquiry.py) | Branches, invented facts, crash/resume, isolation; Postgres end to end including M1 pricing |

## Implemented M4 drafting, approval and portal
Entry points:
- quotation jobs in the worker;
- portal and channel routes in the API ([api/app.py](../../src/quotation_app/api/app.py));
- the React app in [portal/](../../portal/src/app/App.tsx).

See [quotation approval](../features/quotation-approval.md).

| Actual file | Responsibility |
|---|---|
| [domain/quotations.py](../../src/quotation_app/domain/quotations.py) | Statuses, DecisionCommand, version content and hash, review text, approval errors |
| [ports/approvals.py](../../src/quotation_app/ports/approvals.py), [ports/quotations.py](../../src/quotation_app/ports/quotations.py), [ports/channels.py](../../src/quotation_app/ports/channels.py), [ports/identity.py](../../src/quotation_app/ports/identity.py) | Decision unit of work; quotation read, revision and workflow stores; channel bindings, references and notifier; identity and sessions |
| [application/approvals.py](../../src/quotation_app/application/approvals.py) | ApprovalService: the one decision path for portal and channels |
| [application/quotations.py](../../src/quotation_app/application/quotations.py) | List, detail, re-priced revisions |
| [application/channel_actions.py](../../src/quotation_app/application/channel_actions.py) / [notifications.py](../../src/quotation_app/application/notifications.py) | Enrollment and channel decisions / review delivery job |
| [application/sessions.py](../../src/quotation_app/application/sessions.py) | Session tokens, expiry, CSRF |
| [workflows/quotation.py](../../src/quotation_app/workflows/quotation.py) | Approval graph with interrupts; QuotationJobHandler (run lock, stale-resume protection) |
| [adapters/identity/dev.py](../../src/quotation_app/adapters/identity/dev.py) | Development login (the OIDC adapter goes next to it) |
| [adapters/channels/simulated.py](../../src/quotation_app/adapters/channels/simulated.py) | Simulated provider: outbox files, HMAC signatures |
| [api/auth.py](../../src/quotation_app/api/auth.py), [api/portal.py](../../src/quotation_app/api/portal.py), [api/channels.py](../../src/quotation_app/api/channels.py) | Sign-in and session dependencies, tenant routes, signed webhook |
| [persistence/quotations.py](../../src/quotation_app/persistence/quotations.py), [channels.py](../../src/quotation_app/persistence/channels.py), [sessions.py](../../src/quotation_app/persistence/sessions.py) | SQL stores, advisory run lock, job queuing in the same transaction |
| [0005_approvals.py](../../migrations/versions/0005_approvals.py) | M4 tables, append-only triggers, column grants, narrow RLS policies |
| [scripts/simulated_channel.py](../../scripts/simulated_channel.py) | Play the manager's phone: inbox, enroll, decide |
| [portal/src/](../../portal/src/app/App.tsx) | React portal organised by feature (auth, tenant, quotations, enquiries, channels) and layer (model, api, services, store, hooks, ui, routes). See [portal architecture](portal-architecture.md). Tests live in [portal/tests/](../../portal/tests/architecture.test.ts), mirroring src |
| [tests/unit/conftest.py](../../tests/unit/conftest.py) | In-memory M4/M5 "database" and harness used by unit tests |

## Implemented M5 quotation PDFs and delivery
Entry points:
- the `approved` workflow step (queues delivery);
- the `deliver_quotation` job in the worker;
- PDF and delivery routes in the portal API and the enquiry API.

See [quotation delivery](../features/quotation-delivery.md) and [adding channels](adding-channels.md).

| Actual file | Responsibility |
|---|---|
| [domain/documents.py](../../src/quotation_app/domain/documents.py) | Delivery statuses, DocumentSource, recipient rule, document IDs/keys, document errors |
| [ports/documents.py](../../src/quotation_app/ports/documents.py) | QuotationRenderer, DeliveryChannel (+ outcomes), DeliveryStore, DocumentReader |
| [application/delivery.py](../../src/quotation_app/application/delivery.py) | QuotationDeliveryHandler: render once, compare-and-set, record honest outcomes |
| [application/documents.py](../../src/quotation_app/application/documents.py) | QuotationDocumentService: previews, verified approved files, customer view and downloads |
| [adapters/documents/pdf.py](../../src/quotation_app/adapters/documents/pdf.py) | ReportLab renderer: deterministic, escaped, refuses unsupported characters |
| [adapters/delivery/api.py](../../src/quotation_app/adapters/delivery/api.py) | API pull channel (makes the document available) |
| [api/pdf.py](../../src/quotation_app/api/pdf.py) | Download response headers, integrity-failure response |
| [persistence/documents.py](../../src/quotation_app/persistence/documents.py) | `queue_delivery` (outbox row + job), SqlDeliveryStore, SqlDocumentReader |
| [0006_documents.py](../../migrations/versions/0006_documents.py) | quotation_documents (append-only) and quotation_deliveries, RLS, column grants |
| portal `features/quotations` | `DocumentPanel`, `DeliveryList`, `deliveryService.ts`, `useQuotationDocuments.ts` |

## Implemented M6 customer acceptance
See [customer acceptance](../features/customer-acceptance.md).

| Actual file | Responsibility |
|---|---|
| [domain/acceptance.py](../../src/quotation_app/domain/acceptance.py) | Customer statuses, outcomes, price comparison, validity, answer fingerprints |
| [ports/acceptance.py](../../src/quotation_app/ports/acceptance.py) | ResponseStore (offers, atomic recording under a lock) |
| [application/acceptance.py](../../src/quotation_app/application/acceptance.py) | QuotationResponseService (respond/withdraw/expire), expiry and notice job handlers |
| [persistence/acceptance.py](../../src/quotation_app/persistence/acceptance.py) | SqlResponseStore: row-locked recording, revised version, resume/notice jobs |
| [0007_acceptance.py](../../migrations/versions/0007_acceptance.py) | Validity setting and column, quotation_responses (append-only), new statuses |
| portal `features/quotations` | `CustomerPanel`, `customerService.ts`, `useCustomerAnswer.ts`, list filters |

## Planned modules

| Proposed location | Responsibility |
|---|---|
| src/quotation_app/api/ | HTTP routes, auth dependency and webhook handling |
| src/quotation_app/domain/ | Business models, money, pricing and policy rules |
| src/quotation_app/application/ | Use cases, transaction boundaries and authorization |
| src/quotation_app/application/negotiation/ (later) | Counteroffer lifecycle reusing existing quotation/approval services; deferred |
| src/quotation_app/application/manager_commands/ (later) | Verified stock enquiries and scoped change requests through existing services; deferred |
| src/quotation_app/workflows/ | LangGraph state, nodes, routing and versioning |
| src/quotation_app/ports/ | Typed interfaces for channels, ERP, model and storage |
| src/quotation_app/adapters/ | Provider-specific implementations and simulated ERP |
| src/quotation_app/persistence/ | Repositories, tables, tenant context and checkpoint access |
| src/quotation_app/workers/ | Jobs, scheduler, outbox and reconciliation |
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
