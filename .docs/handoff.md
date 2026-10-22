# Current handoff
Updated: 2026-10-22.

## Current state
- **Current milestone: M2 (intake)** is implemented and verified against local PostgreSQL, but not yet committed.
- **M1** is committed locally as 5d1ae69 and not pushed.
- **M0** is COMPLETE (local and CI); commits c6d163c and c6c63dc are on origin/main.
- **CI for M1 and M2** runs after push. Neither milestone is marked complete until it passes.
- Public [repository](https://github.com/nikunjramani/ai-sales-quotation-order-processing), branch main. The user's local `.vscode/settings.json` is intentionally untracked.
- No AI integration, real channel or ERP connection, approval, PDF, order or deployment exists yet.

## Implemented
- **M0:** foundation. See [setup](development/setup.md) and [configuration](development/configuration.md).
- **M1:** deterministic pricing and tenant context. See [quotation pricing](features/quotation-pricing.md) and [ADR 0010](adr/0010-deterministic-pricing-and-tenant-context.md).
- **M2:** see [enquiry intake](features/enquiry-intake.md), [ADR 0011](adr/0011-durable-intake-and-jobs.md) and the [code map](development/code-map.md).
  - Per-tenant API keys (hashed, revocable; new `intake_service` role) and `POST/GET /api/v1/enquiries` with `Idempotency-Key` replay and 409 conflict.
  - A canonical inbox envelope.
  - An atomic receipt (inbox + enquiry + attachments + job, with 202 only after commit).
  - Attachment quarantine and inspection in tenant-scoped local storage.
  - A PostgreSQL job queue (SKIP LOCKED, leases, fencing tokens, backoff with jitter, dead jobs) and a worker process (`python -m quotation_app.worker`).
  - Migration 0003.
- **Infrastructure (M2):**
  - A `quotation_worker` database role and a `quotation_test` database. The role script is idempotent and safe to re-run on an existing volume.
  - `init_local_env.py --add-missing`.
  - `check_database.py` now migrates both databases, tests only against `quotation_test`, and has `--cycle`. CI uses it.
  - `scripts/create_api_key.py`.
  - Integration tests refuse non-`_test` databases.

## Decisions recorded
- **ADR 0011:** API keys as interim authentication and long-term service accounts; PostgreSQL as the job queue; worker role scoped to the queue; quarantine first, with content inspection that is not antivirus.
- **ADR 0010:** pricing defaults (per-line rounding, tax on the subtotal, no discounts, administrators are not approvers) still await pilot validation.
- **Earlier decisions still stand:** ADR 0007 supersedes 0005; negotiation is deferred (ADR 0008); every negotiated revision needs manager approval; direct email approval is confirmed. See the [ADR index](adr/README.md).

## Verification (M2, 2026-10-22)
- Ruff lint/format and mypy (strict, 79 files) pass.
- Offline pytest: 153 unit tests passed, 23 integration tests skipped.
- `scripts/check_database.py --cycle`: `quotation_dev` and `quotation_test` upgraded to 0003_intake with no drift; 176 passed; downgrade base -> upgrade head -> 176 passed again.
- The integration tests found and fixed a real bug: a NULL retry delay needed an explicit type cast in the fenced job update.
- Local upgrade without data loss: `--add-missing` appended the worker settings; recreating the container kept the volume; the role script created `quotation_worker` and `quotation_test`; a re-run was a no-op.
- **Manual end-to-end with real processes:**
  - Created an intake key; uvicorn `/health/ready` returned 200.
  - curl POST with a PDF returned 202; GET showed `quarantined`; an unauthenticated GET returned 401.
  - `python -m quotation_app.worker --once` logged the job as succeeded; GET showed `ready_for_extraction`, with the file under `var/storage/tenants/<tenant>/clean/`.
  - The server log had no secret-like lines. The server was stopped, the smoke-test key revoked, and the temporary token file deleted.
  - The smoke enquiry remains in `quotation_dev` (synthetic).
- The local database container keeps running with its named volume.
- **Not yet run:** GitHub Actions for M1 and M2 (needs push).
- **Known CI warnings:** actions/checkout@v4 and setup-python@v5 target deprecated Node 20; ubuntu-latest is migrating to Ubuntu 26.

## Known gaps (tracked, not blocking M2)
- Content inspection is not malware scanning; a scanner is a gate before real files.
- No cleanup job for quarantine files orphaned by a crash before commit.
- No operator view of dead jobs.
- The request-size limit relies on `Content-Length`; a proxy limit is needed in deployment.
- Local disk storage only.
- OCR and scanned-PDF support are undecided (M3).

## Next task
1. With user authorization, commit M2 and push M1 and M2 to main. Confirm CI (`check_database.py --cycle`) passes, then mark M1 and M2 complete in the roadmap, ADRs 0010-0011 and this handoff.
2. Then start M3 (AI and graph): bounded text/PDF extraction, structured requirements, product matching against `ErpReader.search_products`, LangGraph branches and persistent checkpoints, consuming enquiries in `ready_for_extraction` through a new job kind.
   - **Before starting:** the user must choose a model provider and budget (open decision).
   - **Safety rule:** AI output never sets prices, stock or permissions; the M1 calculator does that.
- Update this handoff in every change; never mark milestones complete without evidence.
