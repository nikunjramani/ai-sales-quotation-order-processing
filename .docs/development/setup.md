# Local setup and M0 walkthrough
Status: foundation implemented. Live PostgreSQL verification passed locally on 2026-10-22; the remote GitHub Actions run is still pending.

## Concepts
Python runs the application. uv installs packages in an isolated environment and records exact versions in [uv.lock](../../uv.lock).
FastAPI provides HTTP endpoints. SQLAlchemy manages database connections and describes tables. Alembic applies versioned schema changes called migrations.
PostgreSQL stores records; row-level security filters them by tenant context. Docker Compose defines the local database service.
Ruff checks style, mypy checks types, pytest tests behaviour, and GitHub Actions describes automated checks. Starlette's test client requires httpx2 (the maintained successor of httpx), so it is a dev dependency.

## Verified offline commands
Run from the repository root:
```powershell
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```
Default pytest explicitly skips PostgreSQL integration tests. Passing this subset does not complete M0.

Generate local credentials once:
```powershell
uv run python scripts/init_local_env.py
```
Already run on this workstation. It creates an ignored .env with random development-only passwords, prints no secrets and refuses to overwrite an existing file.

Preview schema changes:
```powershell
uv run alembic upgrade head --sql
```
This was verified; generating SQL does not prove it executed on PostgreSQL.

## Database prerequisite and pending checks
Verified workstation: Python 3.13.14, uv 0.13.1, Git, Docker Desktop 4.96.1 (engine 29.9.2, Linux containers) and Compose v5.6.0.
Docker Desktop needs the Windows Virtual Machine Platform/WSL features (administrator access and a restart). If `docker compose` reports a missing dockerDesktopLinuxEngine pipe, the engine is not running: start Docker Desktop or run `docker desktop start`, then confirm `docker info` shows a Server section. OS setup can require administrator access and a restart; these changes were not attempted automatically.
See [Docker Windows setup](https://docs.docker.com/desktop/setup/install/windows-install/).

Once Docker works:
```powershell
docker compose up -d --wait
uv run python scripts/check_database.py
uv run python -m quotation_app.persistence.seed
```
Verified 2026-10-22: the container became healthy, the helper reported no schema drift and 9 tests passed, and the seed ran twice without changes. The helper restricts its target to local quotation_dev, upgrades migrations, checks model/schema consistency and runs integration tests. It passes credentials to subprocesses in memory, without printing them. Fixtures insert two fictional tenants; the helper does not downgrade/drop the database.

Compose binds PostgreSQL to loopback port 55432. Bootstrap creates separate migration-owner and runtime roles and runs only on first volume initialization. Editing .env later does not change passwords in an existing database; use an explicit rotation procedure.
docker compose down stops the database while retaining its named volume. Do not casually add -v: that deletes local database data.

## API
```powershell
uv run uvicorn quotation_app.api.app:create_app --factory --host 127.0.0.1 --port 8000
```
Visit http://127.0.0.1:8000/docs, /health/live or /health/ready.
Verified against live PostgreSQL: /health/live 200 ok, /health/ready 200 ready, /docs 200. The server was stopped afterwards.
Liveness returns 200 when the application works. Readiness requires the expected schema and an acceptable runtime role; it returns sanitized 503 when the database is missing or unsuitable.

## Boundaries and troubleshooting
The initial tenant registry and RLS are persistence groundwork, not complete request authorization. No endpoint exposes tenant data. M1 adds trusted tenant context/repositories; M4 adds real identity integration.
No AI model, ERP, messaging provider, approval or order processing is implemented.
Missing URL: generate .env from the root or configure settings explicitly. Readiness 503: check database availability, migrations and runtime role. Integration failure: fix it; never substitute SQLite or silently skip required checks.
