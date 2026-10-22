-- Creates the application roles. Idempotent: it runs automatically when the development
-- volume is first initialized, and can be re-run on an existing volume to add new roles:
--   docker compose exec -T postgres psql -U postgres -d quotation_dev -v ON_ERROR_STOP=1 \
--     -f /docker-entrypoint-initdb.d/01-roles.sql
-- psql quotes variables as SQL literals; secrets are read from the container environment.
\getenv owner_password POSTGRES_OWNER_PASSWORD
\getenv app_password POSTGRES_APP_PASSWORD
\getenv worker_password POSTGRES_WORKER_PASSWORD

-- quotation_owner: runs migrations and seeds. quotation_app: API runtime.
-- quotation_worker: background jobs; may see the job queue across tenants, nothing else.
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS',
    role_name, role_password)
FROM (VALUES
    ('quotation_owner', :'owner_password'),
    ('quotation_app', :'app_password'),
    ('quotation_worker', :'worker_password')
) AS wanted(role_name, role_password)
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = wanted.role_name)
\gexec

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO quotation_owner;
GRANT USAGE ON SCHEMA public TO quotation_app, quotation_worker;
GRANT CONNECT ON DATABASE quotation_dev TO quotation_owner, quotation_app, quotation_worker;

-- Separate database for integration tests, which may truncate tables between tests.
-- Integration tests refuse to run against a database whose name does not end in _test.
SELECT 'CREATE DATABASE quotation_test OWNER quotation_owner'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'quotation_test')
\gexec
GRANT CONNECT ON DATABASE quotation_test TO quotation_owner, quotation_app, quotation_worker;
\connect quotation_test
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO quotation_owner;
GRANT USAGE ON SCHEMA public TO quotation_app, quotation_worker;
