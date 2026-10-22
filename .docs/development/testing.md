# Testing and AI evaluation
## Test layout
```text
tests/
  conftest.py          Shared options, fixtures and in-memory fakes for every test
  unit/                Offline; folders mirror src/quotation_app
    domain/  application/  ports/  adapters/erp/  adapters/storage/  api/  persistence/
    test_config.py  test_architecture.py
  integration/         Real PostgreSQL (quotation_test only); auto-marked `integration`
    conftest.py        Database settings, engines, cleanup, API-key and storage fixtures
    api/  persistence/
```
Rules:
- A unit test for `src/quotation_app/<path>/<module>.py` lives in `tests/unit/<path>/test_<module>.py`. Integration tests follow the same mirroring under `tests/integration/`.
- `tests/` has no `__init__.py` files. Pytest runs with `--import-mode=importlib` and mypy with `explicit_package_bases`, so names such as `domain/test_pricing.py` and `application/test_pricing.py` can coexist.
- Shared setup lives in fixtures, not copied helpers. Test modules never import `conftest.py`.
- Every test under `tests/integration/` is marked `integration` automatically. A test elsewhere can opt in with the marker, for example a future real-ERP contract case.
- **Safety:** integration tests empty the intake and job tables before each test, so every `TEST_*` URL must name a database ending in `_test`. Otherwise the run fails immediately. Development data in `quotation_dev` is never touched.

Shared fixtures in [tests/conftest.py](../../tests/conftest.py):

| Fixture | Provides |
|---|---|
| `now` | Fixed timezone-aware "current time" used by test clocks |
| `industrial_tenant`, `office_tenant` | The two seeded demo tenant IDs |
| `make_context(tenant_id, role)` | A TenantContext with one role |
| `make_policy(tenant_id, currency)` | Synthetic pricing policy (2 decimals, half_up, 18% tax, 15/5 min freshness) |
| `simulated_erp` | Demo catalogues for both tenants, ERP clock fixed at `now`; `.failures` injects errors |
| `membership_reader`, `policy_reader` | In-memory fakes; tests edit `.rows` / `.policies` |
| `memory_storage` | In-memory ObjectStorage; `.objects` to inspect, `.fail_puts` to simulate disk errors |
| `intake_store` | In-memory IntakeStore; `.fail_record` and `.concurrent_winner` simulate failures and lost races |
| `api_key_reader` | In-memory ApiKeyReader; tests add records to `.records` |

[tests/integration/conftest.py](../../tests/integration/conftest.py) adds:

| Fixture | Provides |
|---|---|
| `integration_settings` | Settings built only from `TEST_*` URLs (checked for `_test`), with storage in a temporary folder |
| `owner_engine`, `runtime_engine`, `worker_engine` | One engine per database role; `runtime_engine` also seeds demo data |
| `clean_intake_tables` (automatic) | Truncates intake and job tables before each test |
| `make_api_key(tenant_id, role)` | Creates a key with owner credentials and returns its token |
| `storage` | LocalObjectStorage under the temporary storage folder |

## Current checks (M0-M2)
Run uv run ruff check ., uv run ruff format --check ., uv run mypy and uv run pytest from the root; `uv run pytest tests/unit` runs only the unit tests.

Result on 2026-10-22: 153 unit tests passed and 23 integration tests were skipped. With PostgreSQL via `check_database.py --cycle`, all 176 passed, then passed again after a downgrade to empty and re-upgrade.

| Suite | Checks |
|---|---|
| [unit/domain/test_pricing.py](../../tests/unit/domain/test_pricing.py) | Exact totals, tenant rounding mode, absent price never zero, quantity/minimum/step/unit rules, stale/not-effective/wrong-currency/wrong-unit prices, five stock statuses, all issues reported together |
| [unit/domain/test_money.py](../../tests/unit/domain/test_money.py) / [unit/domain/test_tenancy.py](../../tests/unit/domain/test_tenancy.py) | Float rejection, rounding, precision-loss trap, role permissions |
| [unit/domain/test_intake.py](../../tests/unit/domain/test_intake.py), [test_attachments.py](../../tests/unit/domain/test_attachments.py), [test_jobs.py](../../tests/unit/domain/test_jobs.py) | Intake limits, fingerprint sensitivity, idempotency-key rules, envelope; type sniffing, renamed/binary/encrypted/active-content files rejected; backoff doubling, cap and jitter |
| [unit/application/test_pricing.py](../../tests/unit/application/test_pricing.py) | Permission checked before ERP calls, cross-tenant SKU invisible, ERP errors propagate, stale ERP data, missing/foreign policy refused |
| [unit/application/test_tenancy.py](../../tests/unit/application/test_tenancy.py) | Membership-based tenant resolution |
| [unit/application/test_intake.py](../../tests/unit/application/test_intake.py) | Quarantine write, replay returns original, conflict, cleanup after database/storage failure, lost race returns winner, permission, tenant-scoped status |
| [unit/application/test_api_keys.py](../../tests/unit/application/test_api_keys.py) | Context from key, only hash stored, identical failure for wrong/revoked/unknown/malformed keys |
| [unit/application/test_preparation.py](../../tests/unit/application/test_preparation.py) | Clean files released, rejected files stay quarantined, needs_review, crash-between-move-and-record recovery, permanent errors |
| [unit/application/test_jobs.py](../../tests/unit/application/test_jobs.py) | Complete, retry with backoff (error type only), dead after last attempt, permanent error, unknown kind, lost lease tolerated |
| [unit/ports/test_erp_contract.py](../../tests/unit/ports/test_erp_contract.py) | Shared ERP contract; register new adapters in `ADAPTERS` |
| [unit/adapters/erp/test_simulated.py](../../tests/unit/adapters/erp/test_simulated.py) | Simulated-ERP specifics: unconfigured tenant, failure injection, unknown stock, warehouse, invalid search |
| [unit/adapters/storage/test_local.py](../../tests/unit/adapters/storage/test_local.py) | Put/get/move/delete, no leftover temp files, path traversal and non-generated keys rejected |
| [unit/api/test_enquiries.py](../../tests/unit/api/test_enquiries.py) | 202/200/409 replay contract, tenant-scoped 404, 401 variants, `tenant_id` in body rejected, 422/403, missing key, 413, 503 stores nothing |
| [unit/api/test_app.py](../../tests/unit/api/test_app.py), [unit/test_config.py](../../tests/unit/test_config.py), [unit/persistence/test_seed.py](../../tests/unit/persistence/test_seed.py) | Health endpoints, settings validation, production seed refusal |
| [unit/test_architecture.py](../../tests/unit/test_architecture.py) | Domain/ports/application/adapters import boundaries |
| [integration/persistence/test_tenancy.py](../../tests/integration/persistence/test_tenancy.py) | Runtime role: cross-tenant membership denied, rows invisible without/across context, cannot add memberships or change policies, per-tenant policies, end-to-end pricing |
| [integration/api/test_enquiries.py](../../tests/integration/api/test_enquiries.py) | API to worker to status end to end; replay/conflict store one row; 8 concurrent duplicates create exactly one enquiry and one file; failed transaction leaves no rows or files; cross-tenant 404, revoked key 401; API role cannot read jobs |
| [integration/persistence/test_jobs.py](../../tests/integration/persistence/test_jobs.py) | Cross-tenant claims with SKIP LOCKED, crashed worker reclaimed and stale completion rejected, backoff delays claims, expired final attempt becomes dead, worker role sees only the queue |
| [integration/persistence/test_api_keys.py](../../tests/integration/persistence/test_api_keys.py) | API role sees no keys, or only the presented one |
| [integration/persistence/test_database.py](../../tests/integration/persistence/test_database.py), [test_seed.py](../../tests/integration/persistence/test_seed.py), [integration/api/test_app.py](../../tests/integration/api/test_app.py) | Readiness and owner-role rejection, idempotent seed, tenant visibility, context cleared on pooled connections, denied runtime writes |

Run [check_database.py](../../scripts/check_database.py) only after local PostgreSQL starts. It migrates and checks `quotation_dev` and `quotation_test`, then runs every test against `quotation_test`. With integration tests enabled, missing or non-`_test` URLs make the run fail; by default they are skipped visibly.

CI runs `check_database.py --cycle` on a fresh environment. Remote GitHub Actions [run 39734937763](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39734937763) passed the M0 sequence; CI for M1-M2 runs after push.

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
