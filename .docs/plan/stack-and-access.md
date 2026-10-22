# Stack and access
## Planned stack
Exact versions are intentionally unpinned in this documentation-only baseline. M0 verifies compatibility and creates a reproducible lockfile.

| Component | Choice | Purpose |
|---|---|---|
| Language/package management | Supported Python + uv | Application and reproducible dependencies |
| API and validation | FastAPI + Pydantic | HTTP boundary and validated contracts |
| AI | LangChain model/tool interfaces | Structured extraction and constrained tool usage |
| Workflow | LangGraph + PostgreSQL checkpointer | Branching, persisted state and human interrupts |
| Business database | PostgreSQL + SQLAlchemy + Alembic | Records, constraints and migrations |
| Background work | PostgreSQL job table, leased workers, scheduler and transactional outbox | Durable jobs without introducing a separate broker initially |
| Portal | FastAPI-rendered Jinja templates, ordinary forms initially | Authenticated enquiry/quotation/approval screens |
| Identity | Standards-based OIDC provider, selected before M4 | Login; local role/tenant membership authorization |
| Documents | PDF renderer selected by M5; S3-compatible object storage | Immutable quotation PDFs and private attachments |
| Operations | Docker Compose locally; CI checks; structured logging and OpenTelemetry-compatible instrumentation | Reproducible services and operational visibility |
| Quality | pytest, Ruff, type checking, adapter contracts and AI evaluations | Business correctness and regression prevention |
| Integration automation | Optional n8n | Peripheral triggers and notifications through authenticated APIs |

PostgreSQL is the integration-test and development database from the start; SQLite is not the production path.
A queue library/broker such as Redis-based infrastructure is introduced only through an ADR if measured concurrency or delivery needs justify it.
A vector database is not required for stock or price retrieval.
Frontend framework, hosting vendor, model vendor, identity vendor, and PDF library remain explicit selection tasks, not hidden assumptions.

## Access by stage
| Access | Stage | Who provides it / restrictions |
|---|---|---|
| Python, Git, Docker engine; Windows virtualization/WSL if needed | M0 | Developer; verify installation rather than assuming executable aliases work |
| Model API credentials and budget | M3 | Developer/organization; use secret storage and synthetic examples |
| OIDC test tenant/client | M4 | Developer; configured callback URLs and role mapping |
| Private object storage and email sandbox | M5 | Developer; restricted test recipients |
| Telegram bot token and reachable HTTPS callback | M7 | Developer; register webhook and validate its secret |
| ERP sandbox API credentials and field/API documentation | M7 | Pilot business; least privilege, scoped read/write capabilities |
| Optional CRM sandbox and n8n instance | M7 | Business/developer; no duplicate orchestration ownership |
| WhatsApp/Instagram business/developer configuration | M10 | Business; confirm current account eligibility, permissions, review, policy and charging requirements |
| Hosting, DNS/TLS, production DB/storage, monitoring and backups | M8-M9 | Deployment owner; separate environments and credentials |

No real customer data or credentials are required for planning or M1. Never put secrets in docs, commits, screenshots, or chat.
Verify n8n licensing against the intended commercial deployment before offering embedded or hosted n8n functionality.
Costs to estimate before pilot: model usage, provider messaging, hosting/database, storage, identity and monitoring. No price estimates are asserted yet.
