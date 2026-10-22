# Learning guide
Learning must explain the real architecture; it must not weaken release requirements.

| Term | Plain explanation | Project use |
|---|---|---|
| Tenant | One business using the application | Keep different businesses separate |
| Adapter | Translator between our format and another system | Add an ERP or messaging channel |
| Approval service | One place that checks and records a manager's decision | Portal and chat use identical business rules |
| Identity binding | Verified link between a staff member and a messaging account | Recognize an authorized manager on Telegram |
| Counteroffer | Customer asks for different price or terms | Future negotiation creates a revised quotation |
| Port | Contract the translator must satisfy | All inventory adapters offer defined lookups |
| LangChain | Model/tool integration building blocks | Ask a model for validated enquiry fields |
| LangGraph | Controller for steps, branches and saved progress | Pause quotation processing for approval |
| State | Information carried through a workflow | Requirements, quote ID and pending action |
| Checkpoint | Saved workflow progress | Resume after restart |
| Idempotency | Repeating an operation has the same business effect | Retried acceptance does not create another order |
| Inbox | Durable record of incoming events | Detect replayed provider events |
| Outbox | Durable record of intended outgoing work | Send only after the business change commits |
| Lease | Temporary ownership of a job | Recover work if a worker dies |
| Reconciliation | Check what actually happened elsewhere | Find whether an ERP order succeeded after timeout |
| ADR | Written architecture decision and reasons | Let a future contributor understand the design |
| Source of truth | System whose value is authoritative | ERP supplies current stock and prices |
| RAG | Retrieve information before model reasoning | Possible future policy/manual lookup |
| Tenant context | Trusted note: this person, this business, these roles | Built only after checking stored membership |
| Role / permission | A job title and the actions it allows | A viewer can look, a sales operator can draft, an approver can approve |
| Row-level security (RLS) | Database filter that hides other businesses' rows | Even a buggy query cannot read another tenant |
| Decimal | Exact base-10 number; floats are approximate | Money never drifts by fractions of a paisa |
| Rounding mode | Tie-break rule for an exact half | half_up: 0.125 -> 0.13; half_even: 0.125 -> 0.12 |
| Protocol | Python's way to describe a port: methods an adapter must have | Simulated and real ERPs both satisfy ErpReader |
| Contract test | One suite every adapter must pass | A new ERP proves it omits unknown SKUs and respects tenants |

M1 trace: run `uv run python scripts/demo_quotation.py`. Every price, unit and stock number comes from the ERP; the calculator only does arithmetic and checks rules. No AI is involved yet.

Teaching sequence: business scenario -> term -> minimal example -> production implementation -> trace inputs/outputs -> test failure -> explain tradeoffs.
For each milestone, show an execution trace with synthetic data. Make clear which values AI interprets and which facts tools retrieve.
