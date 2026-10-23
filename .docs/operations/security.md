# Security and privacy plan
- Use OIDC authentication and tenant-scoped roles: administrator, sales operator, approver and viewer; service accounts have narrower scopes.
- Authenticate callbacks with provider-supported verification, replay protection/deduplication and rate limits.
- Store credential references in business tables; keep encrypted secrets in managed secret storage or protected local environment configuration for development.
- Never send credentials to models. Minimize customer data in prompts; redact sensitive logs/traces.
- Treat PDFs and messages as untrusted. Bound file size/pages/time, validate content types, scan/quarantine before parsing, and isolate risky document processing.
- Do not fetch arbitrary user URLs: constrain attachment retrieval to validated provider/object paths to mitigate SSRF.
- Protect portal sessions with secure cookies, CSRF defenses and output escaping.
- Private documents require authorized short-lived downloads. PDF rendering must not execute untrusted HTML/scripts or fetch unrestricted URLs.
- Audit approvals, external writes, administrative changes and support access. Make audit mutation restricted and observable.
- Bound model calls, token budgets, tool access and retries per tenant. Prompt text never grants permissions.
- Define retention, export and deletion policies before real data; include checkpoints, attachments, tracing and backups.
- Keep development, staging and production credentials/data separate.
- Test tenant isolation in the real PostgreSQL runtime role, not only as database owner.
- Document threat model and unresolved findings before pilot; do not claim regulatory certification.
- Bind manager messaging identities to internal memberships with proof of control. Recheck role/revocation at decision time and restrict allowed conversation contexts.
- Provider webhook verification is necessary but not sufficient: validate the acting manager, task/version, recipient binding and expiry. Forwarded actions and uncorrelated text must not approve anything.
- Mobile channel review may expose commercial documents to provider storage; configure permitted channels and disclosure per tenant. Never include reusable action secrets in model input or logs.

## Implemented controls (M5)
- **Only approved content reaches customers:**
  - Delivery is queued only for the approved current version.
  - Rendering re-checks that an approve decision exists for exactly that version and content hash.
  - Customer API routes show only delivered quotations, and other tenants or unknown IDs get the same 404.
- **Document integrity:** each PDF's SHA-256 is recorded when it is rendered and re-checked on every read. A missing or changed file is never served or sent; the delivery fails visibly and downloads get 500. Document rows are append-only, and the storage key changes with the content, so nothing is overwritten.
- **Safe rendering:**
  - ReportLab builds the PDF from data, with no HTML, scripts or URL fetching.
  - Customer text is escaped before ReportLab's markup parser, so it is printed, never interpreted.
  - Unsupported characters are refused, not replaced.
  - Internal evidence (price lists, stock checks) stays out of customer PDFs.
- **Downloads:** always `attachment` with `Cache-Control: no-store` and `nosniff`. Staff need a session with `quotations:view`; customers need an API key with `enquiries:view` for that tenant.
- **No duplicate sends:** a compare-and-set lets only one worker hand a document over. An uncertain outcome is recorded as `unknown` and never retried automatically.
- **Least privilege:** the worker may update only delivery progress columns, and the API may update only `first_downloaded_at`.

## Implemented controls (M4)
- **Portal sessions:**
  - 256-bit random tokens in `HttpOnly; SameSite=Strict; Path=/api` cookies (Secure in production);
  - only SHA-256 hashes stored, an 8-hour lifetime and server-side logout;
  - state changes need an `X-CSRF-Token` derived from the session;
  - the React app never stores tokens.
- **Dev login:** it asks for no password, so configuration refuses it in production, and it only admits stored members. OIDC is required before any other deployment.
- **Access checks:**
  - Every portal request re-resolves membership for the tenant in the URL; non-members get 404.
  - Every decision re-checks the approve permission, so people who were removed or demoted cannot act on old pages or messages.
  - Every decision also re-checks the content hash and current version (no stale approvals) and forbids approving a version you created.
- **One decision per task**, taken under a row lock:
  - Replays return the original decision; conflicting actions get 409.
  - Decisions and versions are append-only, enforced by grants and triggers.
- **Channel events:**
  - Verified by provider signature (HMAC-SHA256, constant-time) before parsing.
  - Action references are random, stored hashed, single use and expire after 24 h. They only work for the bound account and connection, so forwarded messages fail.
  - Binding an account requires a 10-minute one-time code sent from it; bindings are revocable.
  - All rejections share one generic message.
- **Narrow RLS additions:**
  - A person may list only their own memberships and tenant names (`app.subject`).
  - Sessions are visible only by token hash.
  - The worker gained read access to memberships, tenants and pricing policies, still tenant-scoped.
- **Simulated outbox:** it holds live references in plain files under the git-ignored storage folder, so it is for development only.

## Implemented controls (M3)
- Model output is untrusted: strict JSON schemas with no extra fields, verbatim quote checks against the customer's text, product choices limited to ERP candidates, template (not model-written) customer questions. Prices, stock and permissions never come from a model.
- Customer content is wrapped in data tags; attempts to close the tag are neutralised. Invalid answers go to human review.
- LangGraph checkpoints have no tenant column: only the worker role can access them, always through a tenant-scoped workflow_runs row; API and public access revoked. Document text is not stored in checkpoints.
- Default interpreter is offline; with Ollama, data stays on the local machine. Any hosted provider must be reviewed for data handling before real customer data.

## Implemented controls (M2)
- API keys: 256-bit secrets, only SHA-256 hashes stored, constant-time comparison, one generic 401 for every failure, per-tenant scope and role, revocation. Tokens are printed once and never logged.
- Tenant identity for intake comes only from the key; request bodies with unknown fields (including `tenant_id`) are rejected.
- Uploads are size-limited, stored under server-generated tenant keys (never filenames), quarantined until inspected, and rejected on type mismatch, encrypted PDFs or active PDF content. This is not malware scanning: a scanner is a release gate before real files.
- Job payloads hold references only; job errors record exception types only, never customer text.
- Separate database roles: the API cannot read the job queue; the worker sees only the queue across tenants and needs tenant context for everything else.
- Integration tests refuse to run unless pointed at a `*_test` database.
