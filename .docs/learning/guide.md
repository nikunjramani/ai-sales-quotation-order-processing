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

Teaching sequence: business scenario -> term -> minimal example -> production implementation -> trace inputs/outputs -> test failure -> explain tradeoffs.
For each milestone, show an execution trace with synthetic data. Make clear which values AI interprets and which facts tools retrieve.
