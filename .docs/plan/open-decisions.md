# Open decisions and risks
These are implementation gates, not reasons to block documentation.

| Decision | Working assumption | Resolve by |
|---|---|---|
| First business and goods category | Synthetic B2B industrial products | Before real ERP mapping in M7 |
| First real ERP | Choose from pilot business's existing system | M7; inspect API, sandbox, idempotency, stock semantics |
| Email provider | Deferred by the user (2026-10-23): managers approve in the portal for now; email is added as adapters ([adding channels](../development/adding-channels.md)). One sandbox integration first | M7 |
| Model provider/model | Decided for now (user, 2026-10-22): free first. Default `rules` (offline, no AI); `ollama` local model adapter ready once installed (this VM: 16 GB RAM, no GPU, so small models only; installation may need IT approval). Paid providers (e.g. Claude) can be added through the factory later and compared with the evaluation dataset. Next (user, 2026-10-23, planned): Google Gemini free tier, small model, wait-and-retry when unavailable ([plan](gemini-and-categories.md)) | Before pilot; re-evaluate with real enquiry samples |
| Public demo portal | User idea (2026-10-22), not planned yet: GitHub Pages hosts static files only, so either a static demo with recorded sample data, or Pages plus a separately hosted API/database/worker; never put keys in a public page | The React portal exists (M4); decide before publishing anything |
| Identity provider | Decided for now (user, 2026-10-22): provider-independent login; free dev sign-in (synthetic members, refused in production) implemented in M4; an OIDC adapter (Keycloak, Entra, Google, Auth0...) plugs in later (ADR 0013) | Before any non-development deployment |
| Tax, delivery, discounts, currencies | M1 implements per-line rounding, one tenant tax rate on the subtotal, one currency, no discounts or unit conversion (ADR 0010); values are synthetic | Before pilot; may require per-line/multiple taxes or price lists |
| Quote validity and reservations | Decided (user, 2026-10-23): per-business validity, default 7 days from delivery; no reservation in M6 (ADR 0016). Reservation open for the orders milestone | Orders milestone |
| Customer acceptance verification | Decided (user, 2026-10-23): API key of the same business, naming version + content hash (ADR 0016). Links/other channels later | With each new customer channel |
| Retention and data region | Minimize PII; no invented compliance promise | Before pilot data |
| Hosting, expected volume and SLOs | Single-region initial deployment | M8 capacity testing |
| Channel order | Email + Telegram first, Meta channels later | Revisit if business priority differs |
| Approval thresholds/delegation | M4: every quote needs one approver who did not create the version; no deadlines, escalation, delegation or multi-level policy yet. Never auto-approve on timeout | Before pilot |
| Quote validity | Decided in ADR 0016 (valid until = delivery + tenant days, printed on PDF) | Implemented in M6 |
| Direct email approval verification | User selected direct reply (still required); define trusted inbound evidence and task/version correlation | Before email approval implementation (M7) |
| Manager commercial-command scope | Stock enquiries, price changes and discounts requested; quotation vs price-list/catalogue scope needs explicit resolution | M11; never assume global ERP write authority |
| Approval enrollment/context | Define proof-of-control, allowed private/shared contexts, revocation and additional verification | M4 contract; before each real approval connector |
| Negotiation commercial policy | No assumed discounts, rounds or old-offer validity rules | M11; see negotiation plan |
| Attachment/OCR support | M2 accepts PDF, plain text, PNG and JPEG up to 5 MiB, with magic-byte, encrypted and active-PDF checks. OCR engine, languages and scanned-PDF handling are still open | M3 before claiming extraction support |
| Malware scanning | Not implemented; M2 inspection is not antivirus. Choose a scanner/sandbox (e.g. ClamAV or a cloud service) | Before accepting real customer files (M8 gate) |
| Production object storage | Local disk behind the ObjectStorage port (attachments and, since M5, quotation PDFs); choose S3-compatible/cloud storage with encryption and retention | Deployment (M8) |
| PDF fonts and languages | M5 uses built-in PDF fonts (Western European text only); other characters fail delivery visibly. Embed a Unicode font (e.g. Noto) for the pilot's languages | Before real customer data |
| Orders after acceptance | Moved out of M6 by the user (2026-10-23): ERP order creation, reservation, reconciliation and order confirmation; ask all business questions before starting | Next orders milestone |
| Validity setting screen | `quote_validity_days` is a database setting without a portal screen | When tenant settings are built |
| Resending failed/unknown deliveries | M5 records `failed`/`unknown` with the reason but has no resend or "mark delivered" action; define who may resend and how duplicates are checked | Before pilot (with the first push channel) |
| Quotation PDF content | Synthetic layout: business name, lines, totals, reference. Pilot needs letterhead, addresses, tax IDs, terms and validity date | M6 / pilot business |
| Offer lifecycle | Decided for M6 (ADR 0016): expiry closes; staff withdrawal with reason; any price change refuses and auto-revises; stock ignored. Still open: partial acceptance (not supported) and ERP orders | Orders milestone; pilot business validates policy |
| Human handoff | Define pause owner, authorized resume and post-order change/cancellation escalation | M4/M6 |

## Risks and mitigations
Confirmed decisions: direct email reply approval is required; all future negotiated revisions require manager approval. AI must not negotiate autonomously, even within configured limits.

- Provider account review can delay a channel: use adapters and sandbox intake; do not bypass provider restrictions.
- ERP semantics vary: capability discovery, field mapping, timestamped evidence and contract tests.
- Remote writes can succeed before a timeout: persist intent, reconcile by external reference, escalate unresolved outcomes.
- AI mistakes and prompt injection: constrain model privileges, validate outputs, use deterministic commercial rules.
- Cross-tenant leakage: scope every boundary, use DB constraints/RLS where applicable, test checkpoints explicitly.
- Documentation drift: same-change updates and handoff requirements.
- Overengineering: modular monolith with separate process roles; preserve interfaces before considering microservices.
- Tool/session context loss: portable entry files; no dependence on private agent memory.
