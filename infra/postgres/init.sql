-- Runs only when the development PostgreSQL volume is first initialized.
-- psql quotes variables as SQL literals; secrets are read from container environment.
\getenv owner_password POSTGRES_OWNER_PASSWORD
\getenv app_password POSTGRES_APP_PASSWORD
CREATE ROLE quotation_owner LOGIN PASSWORD :'owner_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE quotation_app LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA public TO quotation_owner;
GRANT USAGE ON SCHEMA public TO quotation_app;
GRANT CONNECT ON DATABASE quotation_dev TO quotation_owner, quotation_app;
