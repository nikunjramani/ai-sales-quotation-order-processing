# Sales Quotation & Order Processing

A multi-business platform, still being built, that turns customer enquiries into checked quotations and, after customer acceptance, into confirmed sales orders.

The goal is a reusable product that many businesses (tenants) can use with their own email or messaging channels and their existing ERP or inventory system. It is also a learning project for LangChain, LangGraph and reliable workflow engineering, so every part is documented in plain language.

> **Status (2026-10-22):** M0 foundation is complete. M1 (tenancy and deterministic pricing) is implemented and verified locally. Customer channels, AI extraction, approvals, PDFs and orders are **not built yet**; see the [roadmap](.docs/plan/roadmap.md).

## What it will do
1. Receive an enquiry from email, Telegram, an API and later WhatsApp or Instagram.
2. Use AI to read the request and match products. AI never sets prices, stock, tax or approvals.
3. Read live prices and stock from the business's own ERP, which stays the source of truth.
4. Calculate the quotation with exact, rule-based arithmetic.
5. Send it to a manager for approval in the portal, by email reply or in a messaging app.
6. Deliver the approved PDF, track the customer's response and create the order in the ERP after acceptance.

## What works today
| Area | Status |
|---|---|
| Project setup, settings, health API (`/health/live`, `/health/ready`) | ✅ M0 |
| PostgreSQL with separate owner and runtime roles; row-level security per tenant | ✅ M0 |
| Tenant membership, roles (administrator, sales operator, approver, viewer) and permission checks | ✅ M1 |
| Deterministic quotation calculator: Decimal money, per-tenant rounding and tax, quantity and unit rules; a missing price is never treated as zero | ✅ M1 |
| ERP contract plus a simulated ERP with two fictional businesses | ✅ M1 |
| Enquiry intake, AI extraction, LangGraph workflow, approvals, PDFs, email/Telegram, orders | ⏳ Planned (M2-M7) |

## Tech stack
Python 3.13, [uv](https://docs.astral.sh/uv/), FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 17 (Docker Compose), pytest, Ruff, mypy (strict) and GitHub Actions. LangChain and LangGraph arrive with M3.

## Quick start
**Prerequisites:** Python 3.13, uv 0.13+, Git, and Docker Desktop with Linux containers running. On Windows, Docker needs the WSL / Virtual Machine Platform features enabled.

```powershell
# 1. Install the locked dependencies
uv sync --locked

# 2. Create local-only database passwords in an ignored .env file (prints no secrets)
uv run python scripts/init_local_env.py

# 3. Start PostgreSQL and wait until it is healthy
docker compose up -d --wait

# 4. Apply migrations, check the schema and run all tests against the database
uv run python scripts/check_database.py

# 5. Load fictional demo businesses, users and pricing policies
uv run python -m quotation_app.persistence.seed

# 6. See a priced quotation, a blocked request and access checks
uv run python scripts/demo_quotation.py
```

Run the API:
```powershell
uv run uvicorn quotation_app.api.app:create_app --factory --host 127.0.0.1 --port 8000
```
Then open http://127.0.0.1:8000/docs.

Stop the database with `docker compose down`. Your data is kept; adding `-v` deletes it.
The full walkthrough and troubleshooting are in the [setup guide](.docs/development/setup.md).

## Running checks
```powershell
uv run ruff check .                 # lint
uv run ruff format --check .        # formatting
uv run mypy                         # strict type checking
uv run pytest                       # unit tests (integration tests are skipped)
uv run pytest tests/unit            # unit tests only
uv run python scripts/check_database.py   # migrations + all tests on local PostgreSQL
```
Integration tests never use your `.env` by accident: they need `--run-integration` plus explicit `TEST_DATABASE_URL` and `TEST_MIGRATION_DATABASE_URL`, which `check_database.py` supplies for the local database. CI runs everything on every push. See [testing](.docs/development/testing.md).

## Project layout
```text
src/quotation_app/
  domain/        Pure business rules: money, tenancy, catalogue facts, pricing
  ports/         Contracts (interfaces) that adapters implement, e.g. ErpReader
  application/   Use cases: resolve tenant context, price a quotation
  adapters/      Implementations of ports, e.g. the simulated ERP
  persistence/   Database models, tenant-scoped repositories, demo seed
  api/           FastAPI app and health endpoints
  config.py      Validated settings from environment / .env
migrations/      Alembic schema migrations
scripts/         Local helpers: credentials, database checks, pricing demo
tests/
  conftest.py    Shared fixtures (tenants, contexts, policies, simulated ERP)
  unit/          Offline tests; folders mirror src/quotation_app
  integration/   PostgreSQL tests; run with --run-integration
infra/           PostgreSQL role bootstrap for Docker Compose
.docs/           Architecture, plans, decisions (ADRs), guides and handoff
```
Domain code imports no framework, database or provider code; [a test](tests/unit/test_architecture.py) enforces this.

## Core rules
- **Tenant isolation:** one business can never see another's data. Membership is checked in the database and PostgreSQL row-level security adds a second guard.
- **ERP is authoritative:** prices and stock come from the business's system, stamped with source and time. Nothing is invented.
- **Deterministic money:** exact `Decimal` arithmetic with named rounding rules, never floats.
- **Human approval:** every quotation, and every future negotiated revision, needs manager approval. AI never negotiates on its own.
- **Untrusted input:** customer text and documents are treated as data, never as instructions.
- **Safe retries:** external actions will use durable jobs, an outbox and idempotency so retries never create duplicate orders.

## Documentation
- [Documentation index](.docs/README.md): start here.
- [Roadmap](.docs/plan/roadmap.md) and [current handoff](.docs/handoff.md): what is done and what is next.
- [System architecture](.docs/architecture/system.md) and [execution flow](.docs/architecture/execution-flow.md).
- [Quotation pricing (M1)](.docs/features/quotation-pricing.md) and [code map](.docs/development/code-map.md).
- [Architecture decisions (ADRs)](.docs/adr/README.md) and the [learning guide](.docs/learning/guide.md).

## Contributing
Read [AGENTS.md](AGENTS.md) before changing code; it applies to people and AI tools alike. Claude's entry point is [CLAUDE.md](CLAUDE.md). Every change updates its docs, tests and the handoff. Use only synthetic data, and never commit `.env` or real customer information.

No licence file has been added yet, so default copyright applies until one is chosen.

Repository: [nikunjramani/ai-sales-quotation-order-processing](https://github.com/nikunjramani/ai-sales-quotation-order-processing)
