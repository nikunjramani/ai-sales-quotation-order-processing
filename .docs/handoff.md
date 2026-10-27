# Current handoff
Updated: 2026-10-23 (M6).

## Current state
- **M0-M6 are COMPLETE** (local and CI), all on origin/main:

  | Milestone | Commit | CI run |
  |---|---|---|
  | M1 | 5d1ae69 | [39738532222](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39738532222) |
  | M2 | d7707eb | [39741408875](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39741408875) |
  | M3 | 52cccd7 | [39747434193](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39747434193) |
  | M4 | 21f0ba5 | [39900219005](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39900219005) (`verify` and `portal` jobs) |
  | M5 | 6f951ec | [39903715921](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39903715921) (both jobs) |
  | M6 | f545201 | [39907493342](https://github.com/nikunjramani/ai-sales-quotation-order-processing/actions/runs/39907493342) (both jobs) |

  For M3 the user could not install Ollama on the corporate VM, so it ships with the free rules interpreter.
- **Last milestone: M6 (customer acceptance), complete.** Next milestone not chosen yet: ask the user first. Decisions taken with the user on 2026-10-23 ([ADR 0016](adr/0016-customer-acceptance.md)): acceptance only (no ERP order or reservation); answers through the API; 7-day default validity from delivery; accept/decline (no PO number); any price change refuses and drafts a revision for approval; stock ignored; expiry closes; staff withdrawal with a reason; a portal plus linked-channel notice; a rejected revision closes.
- **Working rule (user, 2026-10-23):** never push to `main`; every change goes on a new branch with a pull request to `main` (AGENTS.md).
- **Working rule (user, 2026-10-23):** ask before assuming anything. Follow [clarify-before-building](../.claude/skills/clarify-before-building/SKILL.md), which is also in AGENTS.md.
- **User decisions (2026-10-23):**
  - **Email approval is out of scope for now:** managers approve in the portal.
  - Email and other providers must stay **easy to add**; see [adding channels](development/adding-channels.md).
  - PDFs use the existing storage decision (local disk behind `ObjectStorage`, production storage at M8).
  - This is recorded in [ADR 0015](adr/0015-quotation-documents-and-delivery.md); email approval and delivery move to M7.
- **User decisions (2026-10-22):**
  - Free models now, with an easy provider swap later (ADR 0012).
  - A provider-independent login: dev sign-in now, OIDC later.
  - A **separate React portal** (ADR 0013).
  - No paid or live calls.
  - A GitHub Pages demo is an idea only (open decisions).
- The user's `.vscode/settings.json` stays untracked; `.vscode/launch.json`, `tasks.json` and `stop-dev.ps1` (one-click "Run all" with stop-and-restart) are committed. `portal/node_modules` and `portal/dist` are ignored.
- **Not built yet:** real ERP or messaging providers (email, Telegram), orders, OIDC and deployment.

## Implemented
- **M0-M3:** see [setup](development/setup.md), [quotation pricing](features/quotation-pricing.md), [enquiry intake](features/enquiry-intake.md) and [enquiry extraction](features/enquiry-extraction.md).
- **M4:** see [quotation approval](features/quotation-approval.md), [ADR 0013](adr/0013-portal-identity-and-approval-core.md) and the [code map](development/code-map.md).
  - **Drafting:** ready enquiries queue `draft_quotation`. The M1 calculator prices them into an immutable version with a SHA-256 content hash. Unpriceable lines give `pricing_failed`, never a guessed price.
  - **Workflow:** a second LangGraph graph (`quotation-approval-v1`) runs draft -> approval task -> interrupt -> decision -> approved / rejected / revision loop. It uses PostgreSQL checkpoints, a per-run advisory lock, and stale-resume protection.
  - **`ApprovalService.decide`:** one service for the portal and channels. It checks role, pending status, content hash/current version and self-approval under a row lock. One decision per task; replays and conflicts are handled; a reason is required to reject or request a revision.
  - **Sessions:** HttpOnly SameSite=Strict cookie with only the hash stored, plus a CSRF header. The dev login is refused in production.
  - **Simulated manager channel:**
    - enrollment by one-time code;
    - revocable bindings;
    - single-use 24-hour action references per account and task;
    - an HMAC-signed webhook;
    - outbox files;
    - `scripts/simulated_channel.py`.
  - **Portal API** (`/api/v1/tenants/{t}/...`): quotations, decisions, revisions, enquiry exception list, channel linking.
  - **React portal** (`portal/`, Vite + TypeScript, mobile-first): login, lists, version review with stock and price evidence, decision panel, revision form, history, channels and enquiries. The API can serve the built files at `/portal/`.
  - **Portal structure (ADR 0014, user request 2026-10-23):**
    - It is organised by feature (`auth`, `tenant`, `quotations`, `enquiries`, `channels`) and layer (`model`, `api` repository, `services`, `store`, `hooks`, `ui/pages`, `ui/components`, `routes`, `index`), plus `shared/` and `app/`.
    - State: TanStack Query for server data, Zustand for the selected business, URL params for filters, form hooks for local state. React Router hash routes.
    - An architecture test enforces the rules, and tests mirror `src/` in `portal/tests/`. See [portal architecture](development/portal-architecture.md).
  - **Migration 0005:**
    - sessions, quotations, versions, tasks, decisions, enrollments, bindings and action references;
    - append-only triggers;
    - column-level grants;
    - narrow `app.subject` / session RLS policies.
  - **CI:** a new `portal` job (npm ci, typecheck, test, build).

- **M5:** see [quotation delivery](features/quotation-delivery.md) and [ADR 0015](adr/0015-quotation-documents-and-delivery.md).
  - **Approved step:** only the approved current version gets a `quotation_deliveries` outbox row plus a `deliver_quotation` job, in one transaction. The recipient is always the enquiry's sender (for the API, the submitting key).
  - **PDF:**
    - ReportLab 5.0.1 renders it; it is deterministic, escapes customer text, refuses unsupported characters and leaves out internal evidence.
    - It is stored once under `tenants/<t>/documents/<id>` (the ID derives from the PDF hash).
    - It is recorded in the append-only `quotation_documents` table, and its hash is re-checked on every read.
  - **Delivery statuses:** `pending`, `sending`, `available`, `sent`, `failed` (with reason), `unknown` (never resent automatically). `pending` -> `sending` is a compare-and-set.
  - **API pull channel:** `GET /api/v1/enquiries/{id}/quotation(.pdf)` with the client's API key. Only delivered approved versions are visible, and the first download is recorded.
  - **Portal:**
    - preview PDF (marked "not an offer");
    - approved PDF download;
    - delivery status with errors, polled while in progress (`DocumentPanel`, `DeliveryList`, `deliveryService`, `useQuotationDocuments`).
  - **Migration 0006:** documents and deliveries, forced RLS, column grants (worker: progress columns; API: `first_downloaded_at`). It downgrades cleanly; PDF files stay on disk.
  - **Extension points** for email and Telegram: the `DeliveryChannel` and `ApprovalNotifier` adapters plus an inbound route. No business code changes ([adding channels](development/adding-channels.md)).
  - **Dependencies:**
    - `reportlab>=5.0.1,<5.1`;
    - a `pillow>=12.3,<13` constraint (13.0.0 was only 7 days old);
    - dev `types-reportlab` 5.0.0.20261008.
    - The architecture test allows `reportlab` in adapters only.

- **M6:** see [customer acceptance](features/customer-acceptance.md).
  - **Customer API:** `POST /api/v1/enquiries/{id}/quotation/response` (accept/decline the exact version and hash, `Idempotency-Key`). `GET .../quotation` gains `status`, `valid_until`, `content_sha256` and `response_path`.
  - **Acceptance re-pricing:**
    - Accepting re-prices from the ERP. Any difference refuses it: `refused_changed` plus version N+1 created by the system, then manager approval and delivery.
    - Lines that can no longer be priced give `pricing_failed`.
    - ERP down gives 503, and nothing is recorded.
  - **Validity:** valid until is printed on the PDF, and an `expire_quotation` job runs then. An answer after valid until records `expired` immediately.
  - **Staff:** withdrawal (sales operator/approver roles, reason, CSRF) and a portal Customer box (status, validity, answers, withdraw form). List filters: Approved, Accepted, and Declined/expired/withdrawn.
  - **Manager notice:** accept/decline notices go to linked approver channels (`ApprovalNotifier.send_notice`; simulated `notice-<id>.json`).
  - **Workflow:** the graph pauses at `await_customer` after `approved`, and `apply_customer` ends the run or continues to re-approval. The name stays `quotation-approval-v1`.
  - **Migration 0007:**
    - the validity setting, plus `valid_until` (backfilled);
    - `quotation_responses` (append-only, one closing answer, unique idempotency keys);
    - the new statuses and grants.
  - **Test harness:** a controllable clock and delayed jobs.

## Decisions recorded
- **ADR 0013:**
  - Sessions follow the backend-for-frontend pattern, and identity providers stay swappable.
  - Versions are immutable and hash-bound.
  - There is one approval service.
  - Graph pauses use interrupts plus resume jobs.
  - Channel enrollment and references work as described in ADR 0013.
  - ADR 0007 is now partly implemented.
- **ADR 0015 (M5):**
  - Only approved versions get documents, and the documents are hash-checked.
  - The delivery outbox reports outcomes honestly: there are no automatic resends after uncertainty.
  - Delivery goes to the enquiry's sender.
  - Email approval is deferred to M7 by the user.
- **Earlier decisions stand:** ADRs 0010-0012, negotiation deferred (0008), every negotiated revision needs manager approval, and direct email approval stays a requirement (now M7).

## Verification (M6, 2026-10-23)
- **Static checks:** Ruff and strict mypy (155 files) pass.
- **Offline pytest:** 327 unit passed, 44 integration skipped.
- **`check_database.py --cycle`:** at `0007_acceptance` with no drift. 371 passed; then downgrade to empty, upgrade, and 371 passed again.
- **Round trip 0007 -> 0006 -> 0007 with an accepted quotation:**
  - Going down mapped the quotation and run status back to `approved`, removed the 2 M6 jobs and the answers table, and kept the other jobs.
  - Upgrading again was clean.
- **Regression found and fixed:** I had made the intake API map every IntegrityError to 409, which broke intake's "not stored, retry" 503 (caught by a PostgreSQL test). The 409 mapping is now limited to the answer route.
- **Portal:** typecheck passes; 41 tests pass; the build passes (379 kB JS, 118 kB gzip).
- **Live run:** see [setup](development/setup.md#customer-acceptance-m6) (accept, replay, notice, decline, withdraw, filters; no secrets in the logs).
- **Not run:**
  - The portal was not clicked through in a real browser.
  - A live price change (the demo ERP has fixed prices) is covered by unit and PostgreSQL tests.

## Verification (M5, 2026-10-23)
- **Static checks:** Ruff lint/format and strict mypy (148 files) pass.
- **Offline pytest:** 296 unit passed, 39 integration skipped.
- **`check_database.py --cycle`:**
  - Both databases are at `0006_documents`, and `alembic check` finds no drift.
  - 335 passed; then downgrade to empty, upgrade, and 335 passed again.
- **Round trip with M5 data present:**
  - Going down to 0005 removed both tables and the one `deliver_quotation` job, and kept the other 5 jobs and the approved quotation.
  - Upgrading again was clean.
- **Real bug found by the PostgreSQL run and fixed:** the first recipient rule used `sender_external_id`, which for API enquiries is the customer's reference label. `delivery_recipient` now picks the submitting connection for the API, and has a unit test.
- **Portal:** typecheck passes; 36 tests pass (architecture rules included); the build is 375 kB JS (117 kB gzip).
- **Live run** (uvicorn serving `/portal/`, `python -m quotation_app.worker --once` processes, httpx, `quotation_dev`):
  - **Before approval:** the customer got 404, the preview was marked, and the approved PDF gave 404.
  - **After approval and one worker pass:**
    - The delivery was `api available`.
    - The customer JSON showed v1 at 10450.38 INR.
    - The PDF's SHA-256 matched, it contained the total and reference and no preview mark, and it was identical to the staff download.
  - **Download tracking:** the first download was recorded once.
  - **Refusals:** the other tenant's key got 404, and no key got 401.
  - **Repeat runs:** an extra worker pass created nothing new.
  - **Logs:** no API keys appeared in the logs, and both temporary keys were revoked.
- **Not run:**
  - The portal was not clicked through in a real browser (it was unit-tested and built, and `/portal/` returned 200).
  - No real push channel exists, so push outcomes are tested with fakes only.

## Verification (M4, 2026-10-22/23)
- **Static checks:** Ruff lint/format and strict mypy (134 files) pass.
- **Offline pytest:** 260 unit passed, 36 integration skipped.
- **Portal:**
  - `npm run typecheck` passes.
  - `npm test` passes all 27 tests, including the architecture rules, which were shown to reject a UI-to-repository import and a deep cross-feature import.
  - `npm run build` produces 372 kB JS (116 kB gzip).
  - Dependencies are pinned versions at least 14 days old: React 19.3.0, Vite 8.3.3, Vitest 5.0.3, TypeScript 7.0.2, TanStack Query 5.104.1, Zustand 5.0.15, React Router 8.4.0, @types/node 24.19.1.
- **`check_database.py --cycle`:** both databases are at 0005_approvals with no drift. 296 passed; then downgrade to empty, upgrade, and 296 passed again.
- **Targeted round trip with M4 data present:** 0005 -> 0004 removed exactly the M4 tables plus the approval run and its checkpoints, and kept the extraction run. Upgrading again returned to head, and `alembic check` was clean.
- **One M2 test changed on purpose:** the worker role may now read memberships (to notify current approvers), still only with tenant context. The test now asserts that boundary.
- **Live run** (uvicorn serving `/portal/`, `python -m quotation_app.worker --once`, curl, `scripts/simulated_channel.py`):
  - Fan and bolts enquiry -> v1 at 10450.38 INR. The review message was delivered to the enrolled simulated phone.
  - A forwarded copy used by another account -> 403. Approval from the phone -> recorded. A second tap with a different action -> 409. Resume -> approved.
  - Pump enquiry -> `pricing_failed` (price_missing). A revision with the pump again -> 422 with issues. A revision with the 600 mm fan -> v1 at 8130.20 INR, then a new task and notification.
  - The manager's portal approval replayed with the same command -> `replayed=true`.
  - An office user on the industrial quotation -> 404. A request without CSRF -> 403. After logout the cookie gets 401.
  - The server log contained no API token, session token, CSRF token or channel secret. The API key was revoked afterwards.
- **Not run:**
  - The portal was not opened in a real browser; it was built and unit-tested, and its files were served (200).
  - Live Ollama (not installable).

## Known gaps (tracked)
- Dev login only; an OIDC adapter is needed before any non-development deployment.
- No approval deadlines, escalation, delegation or multi-level policy, and no quote validity date (open decisions).
- **M6 gaps:** no ERP orders or reservation; answers through the API only; no portal screen for the validity setting; pre-M6 finished runs do not resume for answers (dev data).
- **M5 gaps:**
  - PDFs use built-in fonts (Western European text only; other characters fail visibly).
  - There is no resend action for `failed`/`unknown` deliveries.
  - The PDF has no letterhead, terms or validity date.
  - Only API pull delivery exists.
- Only the simulated manager channel exists; email (deferred by the user) and Telegram are M7.
- Enquiry exceptions are listed in the portal but cannot be edited or answered there yet. Clarification questions are still not sent.
- Carried over: no OCR, no malware scanner, local storage only, no dead-job view.

## User decisions (2026-10-23, after M6): AI reader and "not found" replies
Implemented on `feat/gemini-and-categories` ([ADR 0017](adr/0017-gemini-reader-and-category-replies.md), [plan](plan/gemini-and-categories.md)). Verified: 339 unit tests, the PostgreSQL suite around the migration cycle, 14/14 evaluation cases (rules), and a live API/worker run; a Gemini worker with an invalid key retried. **Pending:** a live Gemini evaluation once the user has put a key in `.env`.
- **Why:** with the rules reader, "price for tata cars" got the same fixed "which products and quantities?" reply repeatedly.
- **Provider:** Google Gemini free tier, small (Flash-Lite class) model, synthetic/demo data only. Configured generically (user, 2026-10-23: "it should be generic"): `QUOTATION_MODEL=google_genai:gemini-3.5-flash-lite` and `QUOTATION_MODEL_API_KEY` in `.env` (the user creates the key; never in chat or Git). No provider-specific code; the Ollama code was removed.
- **AI down or rate-limited:** wait and retry (no fallback to rules).
- **Not found:** say so and list the business's product **categories** (from the ERP); asking about a category lists its products.
- **Replies:** stay fixed templates; AI only reads enquiries.

## Phase 1 foundations (in progress, branch `feat/phase-1-foundations`)
- **User (2026-10-27):** "start implementation as per plan". PR #5 (the plan) is merged. All phase 1 open questions were answered with the recommendations; see [phase 1 plan §3](plan/platform/implementation/phase-1-foundations.md#user-answers-2026-10-27). Claude may commit and push on this branch, one commit per work item, with a draft PR to `main` (never merging).
- **WI-0 done:** golden tests pin today's behaviour before the refactor:
  - approval request wording;
  - accepted and declined notice wording;
  - simulated outbox file names and JSON keys;
  - the old simulated route's response bodies and 409;
  - `"channel": "api"` in the enquiry status and the portal list (PostgreSQL).
  
  Checks: ruff, mypy, 392 tests on PostgreSQL.
- **WI-1 + WI-3 done:**
  - Domain types and ports: connections, the outbox and templates (wording moved word for word), inbound event types, providers, secrets, `integrations:manage` and new job kinds.
  - Secret stores `local` (AES-256-GCM) and `none`, chosen by entry point; new settings; `init_local_env.py --add-missing` adds `QUOTATION_SECRET_STORE_KEY`. **Run it once, and `uv sync`, after pulling.**
  - The old `Channel`/`ApprovalChannel` enums go when the `api` and `simulated` providers exist (WI-5, WI-9).
- **WI-2 done:** migration `0008_connections` (tables, policies, worker grants, backfill, downgrade) and persistence. API keys create and disable their `api` connection; the seed gives each demo business a `simulated` connection (approvals and catalogue); intake and enrollment link rows to connections; disabled connections get no approval requests. Tests: `test_connections.py` and `test_migrations_0008.py` (upgrade with M6 data, downgrade, upgrade). Checks: `check_database.py --cycle` with 420 tests, twice. One earlier run failed once in `test_versions_and_decisions_are_append_only` and did not repeat in three later runs; watch for flakiness.
- **After pulling:** `uv run alembic upgrade head` and `uv run python -m quotation_app.persistence.seed` (the demo connections).
- **Next:** WI-4 + WI-5 (provider registry, generic hook route, the `api` and `simulated` providers).

## Next task
- **Platform plan for review** (user request 2026-10-23): self-service businesses, generic connectors (WhatsApp, Telegram, Instagram, email, website chat...), product data sources, future orders/payments/inventory. [plan/platform/README.md](plan/platform/README.md); decisions in [07-decisions-needed.md](plan/platform/07-decisions-needed.md). Nothing built until the user answers. Detailed step-by-step plan per phase: [plan/platform/implementation/README.md](plan/platform/implementation/README.md) (shared contracts first).
- Follow-up messages that continue the customer's open enquiry: planned, waiting for the user's confirmation ([plan/conversation-follow-ups.md](plan/conversation-follow-ups.md)).
- Commits, pushes and PRs only with the user's explicit permission each time (AGENTS.md).
0. When the user has a Gemini key in `.env`: run `uv run python scripts/evaluate_extraction.py --model google_genai:gemini-3.5-flash-lite` and record the result in ADR 0017.
1. Optionally open the portal in a browser (use "Run all" in VS Code):
   - Run `npm run dev` in portal/, plus the API and worker.
   - Visit http://localhost:5173/portal/.
   - Follow [setup](development/setup.md#approvals-and-portal-m4).
2. Next milestone (orders or another): ask the user every open question first (clarify-before-building).
- Update this handoff in every change; never mark milestones complete without evidence.
