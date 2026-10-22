# Configuration reference
Implemented in [Settings](../../src/quotation_app/config.py). Explicit constructor values override environment variables, which override the root `.env`.

| Variable | Purpose |
|---|---|
| QUOTATION_DATABASE_URL | Required API runtime URL (`postgresql+psycopg`, explicit host and database) |
| QUOTATION_MIGRATION_DATABASE_URL | Owner URL, needed only for migrations, seed and API-key management; never used as a fallback |
| QUOTATION_WORKER_DATABASE_URL | Worker-role URL, needed only by `python -m quotation_app.worker`; never used as a fallback |
| QUOTATION_STORAGE_DIR | Attachment storage root (default `var/storage`, ignored by Git) |
| QUOTATION_ENVIRONMENT | `development` (default), `test` or `production`; production rejects demo seeding |
| POSTGRES_PASSWORD | Compose bootstrap superuser password |
| POSTGRES_OWNER_PASSWORD / POSTGRES_APP_PASSWORD / POSTGRES_WORKER_PASSWORD | Compose passwords for quotation_owner, quotation_app and quotation_worker |
| TEST_DATABASE_URL / TEST_MIGRATION_DATABASE_URL / TEST_WORKER_DATABASE_URL | Integration-test URLs; each must name a `*_test` database |

Database URL representations and validation messages hide secret inputs. Do not log unwrapped secrets, or rendered Compose configuration that contains passwords.

[.env.example](../../.env.example) contains placeholders. The [local setup generator](../../scripts/init_local_env.py) creates the ignored `.env`, and `--add-missing` appends settings that an older `.env` lacks.

Connect, statement and pool-wait timeouts are 3 seconds, with a pool of 5 and no overflow. These are development defaults, not measured production settings.

**Fixed limits (code constants, not settings):**
- **Intake:** text up to 20,000 characters, up to 5 attachments of 5 MiB each and 15 MiB in total; requests over about 21 MB are refused before the body is read.
- **Jobs:** 5 attempts, a 60 s lease, backoff from 5 s doubling up to 10 min with full jitter, and a 2 s worker poll.

## Database roles and grants
| Role | Can do |
|---|---|
| quotation_owner | Migrations, seed, API-key creation and revocation, test-table truncation. FORCE RLS still applies to row access. |
| quotation_app (API) | SELECT tenants, memberships, pricing policies and alembic_version. SELECT/INSERT inbox_events, enquiries and attachments. INSERT jobs (cannot read them). SELECT only the API key whose ID it presents. |
| quotation_worker | SELECT/UPDATE jobs for all tenants. SELECT inbox_events; SELECT/UPDATE enquiries and attachments, only with the job's tenant context. Nothing else. |

All tenant tables use forced RLS on `app.tenant_id`, so without context nothing is visible.

## Health API contract
- `GET /health/live`: 200 with `{"status":"ok"}`, independent of PostgreSQL.
- `GET /health/ready`: 200 with `{"status":"ready"}`, or 503 with `{"status":"not_ready"}`.

Both are read-only and unauthenticated, and neither exposes tenant data. Readiness checks the migration head (`EXPECTED_REVISION`, currently `0003_intake`) and rejects superuser, bypass-RLS and migration-owner connections. It is not a complete authorization audit.

## Enquiry API contract
`POST /api/v1/enquiries` and `GET /api/v1/enquiries/{id}` require `Authorization: Bearer <API key>`; POST also requires `Idempotency-Key`. Status codes, the request shape and limits are in [enquiry intake](../features/enquiry-intake.md). The OpenAPI schema is served at `/docs`.
