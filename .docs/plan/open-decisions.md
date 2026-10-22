# Open decisions and risks
These are implementation gates, not reasons to block documentation.

| Decision | Working assumption | Resolve by |
|---|---|---|
| First business and goods category | Synthetic B2B industrial products | Before real ERP mapping in M7 |
| First real ERP | Choose from pilot business's existing system | M7; inspect API, sandbox, idempotency, stock semantics |
| Email provider | One sandbox integration first | M5 |
| Model provider/model | Structured-output capable; evaluate cost/quality | M3 |
| Identity provider | OIDC with tenant role assignments | M4 |
| Tax, delivery, discounts, currencies | Synthetic rules; configurable per tenant | Before pilot |
| Quote validity and reservations | No stock reservation on draft; recheck at order | Before M6 |
| Customer acceptance verification | Authenticated portal or scoped expiring acceptance token | M6 threat model and business sign-off |
| Retention and data region | Minimize PII; no invented compliance promise | Before pilot data |
| Hosting, expected volume and SLOs | Single-region initial deployment | M8 capacity testing |
| Channel order | Email + Telegram first, Meta channels later | Revisit if business priority differs |
| Approval thresholds/delegation | All quotes need one authorized internal approver | M4; multi-level policy may follow |

## Risks and mitigations
- Provider account review can delay a channel: use adapters and sandbox intake; do not bypass provider restrictions.
- ERP semantics vary: capability discovery, field mapping, timestamped evidence and contract tests.
- Remote writes can succeed before a timeout: persist intent, reconcile by external reference, escalate unresolved outcomes.
- AI mistakes and prompt injection: constrain model privileges, validate outputs, use deterministic commercial rules.
- Cross-tenant leakage: scope every boundary, use DB constraints/RLS where applicable, test checkpoints explicitly.
- Documentation drift: same-change updates and handoff requirements.
- Overengineering: modular monolith with separate process roles; preserve interfaces before considering microservices.
- Tool/session context loss: portable entry files; no dependence on private agent memory.
