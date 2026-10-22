# Testing and AI evaluation
## Test layout
```text
tests/
  conftest.py          Shared options and fixtures for every test
  unit/                Offline; folders mirror src/quotation_app
    domain/  application/  ports/  adapters/erp/  api/  persistence/
    test_config.py  test_architecture.py
  integration/         Real PostgreSQL; auto-marked `integration`
    conftest.py        Database settings and engine fixtures
    api/  persistence/
```
Rules:
- A unit test for `src/quotation_app/<path>/<module>.py` lives in `tests/unit/<path>/test_<module>.py`. Integration tests follow the same mirroring under `tests/integration/`.
- `tests/` has no `__init__.py` files. Pytest runs with `--import-mode=importlib` and mypy with `explicit_package_bases`, so names such as `domain/test_pricing.py` and `application/test_pricing.py` can coexist.
- Shared setup lives in fixtures, not copied helpers. Test modules never import `conftest.py`.
- Every test under `tests/integration/` is marked `integration` automatically. A test elsewhere can opt in with the marker, for example a future real-ERP contract case.

Shared fixtures in [tests/conftest.py](../../tests/conftest.py):

| Fixture | Provides |
|---|---|
| `now` | Fixed timezone-aware "current time" used by test clocks |
| `industrial_tenant`, `office_tenant` | The two seeded demo tenant IDs |
| `make_context(tenant_id, role)` | A TenantContext with one role |
| `make_policy(tenant_id, currency)` | Synthetic pricing policy (2 decimals, half_up, 18% tax, 15/5 min freshness) |
| `simulated_erp` | Demo catalogues for both tenants, ERP clock fixed at `now`; `.failures` injects errors |
| `membership_reader`, `policy_reader` | In-memory fakes; tests edit `.rows` / `.policies` |

[tests/integration/conftest.py](../../tests/integration/conftest.py) adds `integration_settings` (built only from explicit `TEST_*` URLs), `owner_engine`, and `runtime_engine` (restricted role, seeded data).

## Current checks (M0-M1)
Run uv run ruff check ., uv run ruff format --check ., uv run mypy and uv run pytest from the root. `uv run pytest tests/unit` runs only unit tests. Result 2026-10-22: 73 unit tests passed with 11 integration tests skipped. With PostgreSQL via check_database.py, 84 passed.

| Suite | Checks |
|---|---|
| [unit/domain/test_pricing.py](../../tests/unit/domain/test_pricing.py) | Exact totals, tenant rounding mode, absent price never zero, quantity/minimum/step/unit rules, stale/not-effective/wrong-currency/wrong-unit prices, five stock statuses, all issues reported together |
| [unit/domain/test_money.py](../../tests/unit/domain/test_money.py) / [unit/domain/test_tenancy.py](../../tests/unit/domain/test_tenancy.py) | Float rejection, rounding, precision-loss trap, role permissions |
| [unit/application/test_pricing.py](../../tests/unit/application/test_pricing.py) | Permission checked before ERP calls, cross-tenant SKU invisible, ERP errors propagate, stale ERP data, missing/foreign policy refused |
| [unit/application/test_tenancy.py](../../tests/unit/application/test_tenancy.py) | Membership-based tenant resolution |
| [unit/ports/test_erp_contract.py](../../tests/unit/ports/test_erp_contract.py) | Shared ERP contract; register new adapters in `ADAPTERS` |
| [unit/adapters/erp/test_simulated.py](../../tests/unit/adapters/erp/test_simulated.py) | Simulated-ERP specifics: unconfigured tenant, failure injection, unknown stock, warehouse, invalid search |
| [unit/api/test_app.py](../../tests/unit/api/test_app.py), [unit/test_config.py](../../tests/unit/test_config.py), [unit/persistence/test_seed.py](../../tests/unit/persistence/test_seed.py) | Health endpoints, settings validation, production seed refusal |
| [unit/test_architecture.py](../../tests/unit/test_architecture.py) | Domain/ports/application/adapters import boundaries |
| [integration/persistence/test_tenancy.py](../../tests/integration/persistence/test_tenancy.py) | Runtime role: cross-tenant membership denied, rows invisible without/across context, cannot add memberships or change policies, per-tenant policies, end-to-end pricing |
| [integration/persistence/test_database.py](../../tests/integration/persistence/test_database.py), [test_seed.py](../../tests/integration/persistence/test_seed.py), [integration/api/test_app.py](../../tests/integration/api/test_app.py) | Readiness and owner-role rejection, idempotent seed, tenant visibility, context cleared on pooled connections, denied runtime writes |

Run [check_database.py](../../scripts/check_database.py) only after local PostgreSQL starts. It applies/checks migrations and enables integration tests with explicit URLs. Missing test URLs fail when integration tests are enabled; default skipping is visible.
CI also downgrades/re-upgrades its disposable schema and repeats tests. Local live result 2026-10-22 (M1): check_database.py 84 passed with no schema drift; downgrade base -> upgrade head -> 84 passed again; downgrade to 0001 removed only the M1 tables. Remote GitHub Actions [run 39734937763](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39734937763) passed the M0 sequence from a fresh environment; M1 CI runs after push.

## Planned business suites
- Domain unit tests: Decimal totals, rounding, quantity/unit validation, expiry, pricing policies, missing values.
- PostgreSQL integration tests: real migrations, tenant policies, unique constraints, transactional inbox/outbox, job leases.
- Adapter contracts: every ERP/channel implementation passes shared fixtures; provider sandbox tests validate actual APIs.
- Workflow tests: clarification, rejection, revision, restart/resume, provider failures, model failures, expiry and accepted order.
- Security tests: cross-tenant reads/writes/downloads/checkpoints, forged webhooks, stale approvals, role bypass and attachment handling.
- Concurrency/recovery: simultaneous approvals/acceptances, repeated jobs, worker crash, graph replay, timeout after remote success.
- End-to-end: two tenants and two channels through approved PDF and sandbox ERP order.
- Release tests: backup restore, migration/rollback strategy, deployment smoke tests and documented load profile.

## Additional approval and extension coverage
- Run the same approval contract cases through portal, fake channel and each supported real channel adapter.
- Verify enrolled actor/tenant/context, forwarded actions, revoked roles, expired/stale buttons and conflicting portal/chat decisions.
- Verify full quote review detail is accessible in-channel and provider limitations produce explicit fallback rather than silent approval.
- Confirm notifications across channels reference one task; retries or failed confirmations never duplicate decisions/resumes.
- Add import-boundary checks when modules exist; a new approval provider must not require financial-domain or graph-routing edits.
- Deferred negotiation tests are defined in the [negotiation plan](../plan/negotiation.md); no feature pass is claimed before implementation.
- Direct email decisions must exclude quoted approvals, automatic replies and ambiguous/conditional text, and verify sender plus exact task/version.
- Deferred manager commands must distinguish read-only stock questions from scoped changes, reject ambiguous global price writes and require approval of every negotiated revision, even if the proposed discount is within policy limits.

## Lifecycle and ingestion coverage
- Unsupported, encrypted, oversized and scanned PDFs must not silently produce empty successful requirements. Preserve extraction evidence and route to clarification/review where unsupported.
- Draft previews and final PDFs must match the exact reviewed quotation values/version; previews cannot be dispatched as approved offers.
- Test human pause versus dispatch, authorized resume, cancellation versus order commitment, expired/withdrawn offers and acceptance across multiple revisions of one purchase.
- Order confirmation requires confirmed ERP success; failed confirmation retries must never create another order.

## AI evaluation dataset
Synthetic cases include aliases, misspellings, ambiguous SKUs, multiple items, missing quantities, conflicting dates, units, currencies, malicious instructions and unsupported attachment formats.
Track field extraction correctness, SKU match correctness, appropriate clarification, invented factual values, latency and cost.
Release blocking invariants: no model-origin price/stock accepted as authoritative; no tool authorization from model text; no bypass of approval/tenant checks.
Set measured extraction/latency targets before pilot; do not invent passing scores in advance.
Keep prompt/model/version and dataset version with results. Use deterministic stubs for routine tests and opt-in bounded live model evaluations.
A test that mirrors implementation without asserting business behaviour is insufficient.
