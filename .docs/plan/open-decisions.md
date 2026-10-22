# Open decisions and risks
These are implementation gates, not reasons to block documentation.

| Decision | Working assumption | Resolve by |
|---|---|---|
| First business and goods category | Synthetic B2B industrial products | Before real ERP mapping in M7 |
| First real ERP | Choose from pilot business's existing system | M7; inspect API, sandbox, idempotency, stock semantics |
| Email provider | One sandbox integration first | M5 |
| Model provider/model | Structured-output capable; evaluate cost/quality | M3 |
| Identity provider | OIDC with tenant role assignments | M4 |
| Tax, delivery, discounts, currencies | M1 implements per-line rounding, one tenant tax rate on the subtotal, one currency, no discounts or unit conversion (ADR 0010); values are synthetic | Before pilot; may require per-line/multiple taxes or price lists |
| Quote validity and reservations | No stock reservation on draft; recheck at order | Before M6 |
| Customer acceptance verification | Authenticated portal or scoped expiring acceptance token | M6 threat model and business sign-off |
| Retention and data region | Minimize PII; no invented compliance promise | Before pilot data |
| Hosting, expected volume and SLOs | Single-region initial deployment | M8 capacity testing |
| Channel order | Email + Telegram first, Meta channels later | Revisit if business priority differs |
| Approval thresholds/delegation | All quotes need one authorized internal approver | M4; multi-level policy may follow |
| Direct email approval verification | User selected direct reply; define trusted inbound evidence and task/version correlation | Before email decision implementation |
| Manager commercial-command scope | Stock enquiries, price changes and discounts requested; quotation vs price-list/catalogue scope needs explicit resolution | M11; never assume global ERP write authority |
| Approval enrollment/context | Define proof-of-control, allowed private/shared contexts, revocation and additional verification | M4 contract; before each real approval connector |
| Negotiation commercial policy | No assumed discounts, rounds or old-offer validity rules | M11; see negotiation plan |
| Attachment/OCR support | M2 accepts PDF, plain text, PNG and JPEG up to 5 MiB, with magic-byte, encrypted and active-PDF checks. OCR engine, languages and scanned-PDF handling are still open | M3 before claiming extraction support |
| Malware scanning | Not implemented; M2 inspection is not antivirus. Choose a scanner/sandbox (e.g. ClamAV or a cloud service) | Before accepting real customer files (M8 gate) |
| Production object storage | Local disk behind the ObjectStorage port; choose S3-compatible/cloud storage with encryption and retention | Deployment (M8) |
| Offer lifecycle | Define expiry, withdrawal/replacement, policy-change revalidation and partial acceptance handling; never silently accept different terms | M6; pilot business validates policy |
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
