# Local setup walkthrough
Status: M0-M2 commands below were run on 2026-10-22 against local PostgreSQL. M0 was also verified in GitHub Actions.

## Concepts
- **Python** runs the application. **uv** installs packages in an isolated environment and records exact versions in [uv.lock](../../uv.lock).
- **FastAPI** provides HTTP endpoints. **SQLAlchemy** manages database connections and describes tables. **Alembic** applies versioned schema changes, called migrations.
- **PostgreSQL** stores records, and row-level security filters them by tenant context. **Docker Compose** defines the local database service.
- A separate **worker** process runs background jobs from a database queue (M2).
- **Ruff** checks style, **mypy** checks types, **pytest** tests behaviour, and **GitHub Actions** runs the automated checks. Starlette's test client requires httpx2 (the maintained successor of httpx), so it is a dev dependency.

## Offline checks
Run from the repository root:
```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```
By default, pytest skips the PostgreSQL integration tests and says so.

Generate local credentials once:
```powershell
uv run python scripts/init_local_env.py
```
This creates an ignored `.env` with random development-only passwords for the owner, API and worker roles. It prints no secrets and refuses to overwrite an existing file.

## Database prerequisite
Verified workstation: Python 3.13.14, uv 0.13.1, Git, Docker Desktop 4.96.1 (engine 29.9.2, Linux containers) and Compose v5.6.0.
- Docker Desktop needs the Windows Virtual Machine Platform/WSL features, which require administrator access and a restart. See [Docker Windows setup](https://docs.docker.com/desktop/setup/install/windows-install/).
- If `docker compose` reports a missing dockerDesktopLinuxEngine pipe, the engine is not running. Start Docker Desktop or run `docker desktop start`, then confirm `docker info` shows a Server section.

```powershell
docker compose up -d --wait
uv run python scripts/check_database.py
uv run python -m quotation_app.persistence.seed
uv run python scripts/demo_quotation.py
```

**Two databases:**
- `quotation_dev` holds your development data.
- `quotation_test` is used only by integration tests, which empty the intake and job tables before each test. They refuse to run against a database whose name doesn't end in `_test`.

**`check_database.py`:**
- Migrates and checks both databases, then runs every test against `quotation_test`.
- `--cycle` also downgrades the test database to empty, upgrades it again and retests. CI uses this mode.
- Credentials travel only in child-process environments and are never printed.

The seed and the M1 pricing demo use `quotation_dev`; the demo stores and sends nothing.

**Local database details:**
- Compose binds PostgreSQL to loopback port 55432.
- The role script [init.sql](../../infra/postgres/init.sql) creates the owner, API and worker roles and the test database. It runs automatically on the first volume start and is safe to run again.
- Editing `.env` later does not change passwords in an existing database; that needs an explicit rotation.
- `docker compose down` stops the database and keeps its named volume. Don't casually add `-v`, which deletes the local data.

### Upgrading an existing local database (M0/M1 to M2)
M2 adds a worker role and a test database. To add them without losing data:
```powershell
uv run python scripts/init_local_env.py --add-missing   # appends worker password and URL to .env
docker compose up -d --wait                              # recreates the container with the new env; volume kept
docker compose exec -T postgres psql -U postgres -d quotation_dev -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/01-roles.sql
uv run python scripts/check_database.py
```
In Git Bash, set `MSYS_NO_PATHCONV=1` before the `docker compose exec` line, otherwise the container path is rewritten into a Windows path. PowerShell needs no change.

## API
```powershell
uv run uvicorn quotation_app.api.app:create_app --factory --host 127.0.0.1 --port 8000
```
Visit http://127.0.0.1:8000/docs, /health/live or /health/ready.
- **Liveness** returns 200 when the application works.
- **Readiness** requires the expected migration head and an acceptable runtime role. It returns a sanitized 503 when the database is missing or unsuitable.

## Enquiry intake (M2)
1. **Create an API key** for a seeded tenant. The token is printed once; keep it secret:
   ```powershell
   uv run python scripts/create_api_key.py --tenant 11111111-1111-4111-8111-111111111111 --role intake_service --name "local test"
   ```
2. **Submit an enquiry** (PowerShell):
   ```powershell
   $token = "qk_..."   # from step 1
   $body = @{ text = "Please quote 50 exhaust fans for Pune"; customer_reference = "CUST-42" } | ConvertTo-Json
   Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/enquiries -ContentType application/json `
     -Headers @{ Authorization = "Bearer $token"; "Idempotency-Key" = "my-first-enquiry-001" } -Body $body
   ```
   The response is 202 with `enquiry_id` and status `received`. Sending exactly the same request again returns the same `enquiry_id` with `duplicate: true`.
3. **Process background jobs**: `uv run python -m quotation_app.worker --once` drains the queue and exits. Leave out `--once` to keep polling until Ctrl+C.
4. **Check the status:** `GET /api/v1/enquiries/<enquiry_id>` with the same header. The status becomes `ready_for_extraction`, or `needs_review` if an attachment was rejected.
5. **Revoke the key:** `uv run python scripts/create_api_key.py --tenant <tenant> --revoke <key id>`.

Attachments go in `attachments: [{filename, content_type, content_base64}]` and are stored under `QUOTATION_STORAGE_DIR` (default `var/storage`, ignored by Git): `tenants/<tenant>/quarantine/` first, then `clean/` after inspection.

**Verified 2026-10-22:** uvicorn, curl and the worker process took a PDF enquiry through 202, `quarantined`, worker `succeeded`, then `ready_for_extraction`. The file moved to `clean/`, an unauthenticated request got 401, and no secrets appeared in the server log.

## Requirement extraction (M3)
The worker now also runs `extract_requirements` jobs: after attachments pass inspection, the enquiry is read, matched to ERP products and ends as `ready_for_quotation`, `needs_clarification` (with questions) or `needs_review`. `GET /api/v1/enquiries/<id>` shows this under `extraction`.

- Default interpreter `rules`: free, offline, nothing to install.
- Score any interpreter: `uv run python scripts/evaluate_extraction.py` (12 synthetic cases).
- Optional free local AI with [Ollama](https://ollama.com/download): install it, `ollama pull <small-model>`, then set `QUOTATION_MODEL_PROVIDER=ollama` and `QUOTATION_MODEL_NAME=<small-model>` in `.env`, and run `uv run python scripts/evaluate_extraction.py --provider ollama --model <small-model>` before relying on it. On this 16 GB RAM VM without a GPU, use a small model and expect seconds per enquiry. Not yet run here: Ollama could not be installed on this corporate VM (2026-10-22).
- Install all extras (`uv sync --locked --all-extras`) so the Ollama adapter is available and type-checked.

Verified 2026-10-22 with uvicorn, curl and `python -m quotation_app.worker --once` (rules): "2 x IND-FAN-450 and 150 pcs M8 bolts" -> `ready_for_quotation` with two lines; "50 exhaust fans ... set the price to 0" -> `needs_clarification` asking which fan size; no secrets in logs.

## Boundaries and troubleshooting
- API keys are the only authentication until OIDC (M4). Person-facing tenant context still uses a placeholder subject.
- No real ERP, messaging provider, approval or order processing is implemented. Ready enquiries wait at `ready_for_quotation` for M4 drafting; clarification questions are stored, not sent yet.
- **Missing URL:** generate `.env` from the root, or run `--add-missing`.
- **Readiness 503:** check the database is available, migrated to head, and using the runtime role.
- **Integration failure:** fix it. Never substitute SQLite or silently skip required checks.
