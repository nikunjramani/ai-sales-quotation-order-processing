# Configuration reference
Implemented in [Settings](../../src/quotation_app/config.py). Explicit constructor values override environment variables, which override root .env.

| Variable | Purpose |
|---|---|
| QUOTATION_DATABASE_URL | Required runtime postgresql+psycopg URL with explicit host/database |
| QUOTATION_MIGRATION_DATABASE_URL | Required only for migrations/seed; no fallback to runtime credentials |
| QUOTATION_ENVIRONMENT | development (default), test or production; production rejects demo seeding |
| POSTGRES_PASSWORD | Compose bootstrap superuser password |
| POSTGRES_OWNER_PASSWORD | Compose quotation_owner password |
| POSTGRES_APP_PASSWORD | Compose quotation_app password |
| TEST_DATABASE_URL | Explicit runtime URL for opt-in integration tests |
| TEST_MIGRATION_DATABASE_URL | Explicit owner URL for opt-in integration tests |

Database URL representations and validation messages hide secret inputs. Do not log unwrapped secrets or rendered Compose configuration containing passwords.
[.env.example](../../.env.example) contains placeholders. [Local setup generator](../../scripts/init_local_env.py) generates the ignored .env without overwriting it.
Runtime connect, statement and pool wait timeouts are three seconds; pool size is five with no overflow. These are development defaults, not measured production capacity settings.

## Health API contract
- GET /health/live: 200 with {"status":"ok"}; independent of PostgreSQL.
- GET /health/ready: 200 with {"status":"ready"} or 503 with {"status":"not_ready"}.
Both are read-only and unauthenticated; neither exposes tenant data.
Readiness checks the migration head (`EXPECTED_REVISION`, currently 0002_memberships_policies) and rejects superuser, bypass-RLS and migration-owner membership. It is not a complete authorization audit.

The owner role creates schema objects. Runtime has SELECT only on tenants, memberships, tenant_pricing_policies and alembic_version. Pricing policy values live in the database per tenant, not in environment variables.
Tenant RLS denies visibility without context and filters a supplied context. Database credentials must remain private: trusted application identity/tenant authorization is still required before business endpoints exist.
