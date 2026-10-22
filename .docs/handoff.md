# Current handoff
Updated: 2026-10-22.

## Current state
M0 foundation is COMPLETE (2026-10-22): exit checks passed against live local PostgreSQL and in a fresh GitHub Actions run. Foundation commit c6d163c is pushed to main. No business workflow, AI integration, provider connection, approval/order feature or deployment exists.
Git is on main with the public [repository](https://github.com/nikunjramani/ai-sales-quotation-order-processing). Planning commit f8c2af1 and foundation commit c6d163c are on origin/main. The user's local .vscode/settings.json is intentionally untracked.
Implemented: Python package/lockfile, validated settings, ignored local credential generator, FastAPI health endpoints, PostgreSQL Compose/bootstrap roles, Alembic tenant migration/RLS, synthetic seed, offline and opt-in integration tests, and a GitHub Actions workflow. See [setup](development/setup.md) and [configuration](development/configuration.md).
User requested planning/documentation first, with reusable multi-channel and ERP integration design.
User subsequently authorized creation of this public GitHub repository and publication of the project. A root .gitignore excludes local secrets, Python environments, generated files and runtime data. The initial commit publishes the documentation baseline; it does not implement M0.

## Decisions recorded
Final pre-implementation [review](plan/readiness-review.md) and [flowcharts](architecture/flowcharts.md) remain the target plan. ADR 0009 records the new foundation implementation and its verification limits.
Latest user request authorized starting M0. Preserve manager channel approval, portal access, provider extension boundaries and deferred negotiation.
ADR 0007 supersedes portal-only ADR 0005 while preserving version-bound authorization. ADR 0008 records deferred negotiation scope. New module-boundary and negotiation documents define extension contracts.
User confirmed direct email reply approval and mandatory manager approval for every future negotiated revision; AI must not negotiate autonomously. Added a deferred manager-operations plan for stock enquiries and price/discount requests through email and supported messaging channels at M11. Exact price-change scope (quotation vs price list/catalogue) remains a future clarification; no global write authority is assumed.
See [ADR index](adr/README.md): adapter boundaries, tenant isolation, ERP authority, durable workflows/jobs, approval/versioning and documentation portability.

## Verification
Python 3.13.14, uv 0.13.1, Git 2.55.0, Docker Desktop 4.96.1 (engine 29.9.2, Linux) and Compose v5.6.0 are available. The user enabled the Windows virtualization/WSL prerequisites; the engine was started with docker desktop start. Locked dependencies installed; Ruff lint/format and mypy pass. Offline pytest: 6 passed, 3 PostgreSQL tests explicitly skipped. Offline migration SQL generated and Compose/CI YAML parsed. In-process smoke: liveness 200; readiness 503 with DB absent, as intended.
Live local results 2026-10-22: docker compose up -d --wait -> postgres:17.11-bookworm healthy on 127.0.0.1:55432. scripts/check_database.py -> upgrade head, alembic check reported no drift, 9 passed (3 integration). alembic downgrade base -> upgrade head -> pytest --run-integration 9 passed. Seed ran twice (idempotent). uvicorn smoke: /health/live 200 ok, /health/ready 200 ready, /docs 200; server stopped, log contained no credentials. alembic current: 0001_tenants (head). The local database container is left running with its named volume. Remote [GitHub Actions run 39734937763](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39734937763) on c6d163c passed in 42s: lint, format, mypy, offline pytest 6 passed/3 skipped; fresh credentials and Compose DB healthy; alembic check no drift; integration 9 passed; downgrade base/upgrade head; 9 passed again. CI warnings to address later: actions/checkout@v4 and setup-python@v5 target deprecated Node 20, and ubuntu-latest is migrating to Ubuntu 26. Nine ADRs exist; 0005 is superseded by 0007. Ignored .env was generated locally without printing secrets. No application server remains running.
Documentation validation: 39 Markdown files and 107 local links checked, no broken links. git diff --check and obvious credential-pattern scan passed; .env and .venv are ignored by Git.
Documentation review 2026-10-22: offline checks re-run (Ruff, format, mypy pass; pytest 6 passed, 3 skipped), documented package versions match uv.lock, httpx2 confirmed as Starlette's required test-client dependency (pydantic/httpx2). Stale Docker/push/status statements corrected.
External official references reviewed where accessible. Meta documentation returned HTTP 429; channel-specific eligibility and policy remain implementation verification gates.

## Next task
Start M1 (domain and tenancy): trusted tenant context, role model, product/price/stock contracts, Decimal quotation calculator and simulated ERP, with two-tenant negative tests and rule tests per the roadmap exit gate. Optional maintenance: bump CI actions off Node 20 and consider pinning the runner image.
Before model integration choose provider/budget; before real integrations identify pilot ERP and email provider. These choices do not block M0.
Update this handoff in every implementation change; never mark future milestones complete without evidence.
