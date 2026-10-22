# System flowcharts
Status: planned behaviour. All application milestones remain pending.

## Business flow
```mermaid
flowchart TD
    A[Customer enquiry from supported channel] --> B[Verify business and deduplicate]
    B --> C[Extract requirements and match products]
    C --> D{Details and ERP facts complete?}
    D -- No --> E[Clarification or human review]
    E --> C
    D -- Yes --> F[Calculate immutable draft quotation]
    F --> G[Manager review via portal or verified email/chat]
    G --> H{Decision}
    H -- Revise --> F
    H -- Reject --> X[Close or retain for human handling]
    H -- Approve --> I[Generate and send approved PDF]
    I --> J{Customer response}
    J -- Accept --> K[Verify exact offer and recheck terms/stock]
    K --> L{Valid to fulfil?}
    L -- Changed terms --> F
    L -- Yes --> M[Create ERP order idempotently]
    M --> N{ERP outcome confirmed?}
    N -- Unknown --> O[Reconcile or human review]
    O --> N
    N -- Success --> P[Record order and send confirmation]
    N -- Failure --> E
    J -- Counteroffer --> Q[Human review now; negotiation module in M11]
    Q --> F
    J -- No response --> R[Wait or permitted follow-up until expiry]
    R --> J
    J -- Reject --> X
```
Every revised negotiation offer returns to manager approval. A counteroffer is not customer acceptance. Not every failure is automatically retried; unrecoverable errors remain in human review.

## Module boundaries
```mermaid
flowchart LR
    Channels[Email / Telegram / WhatsApp / other supported channels] <--> Adapters[Transport adapters]
    Portal[Mobile-friendly portal] --> Identity[Identity and permission checks]
    Adapters --> Identity
    Identity --> Services[Application services: enquiry / quotation / approval / order]
    Graph[LangGraph coordinator] --> Services
    Services --> Rules[Deterministic domain rules]
    Services --> AI[LangChain model interface]
    Services --> ERPAdapter[ERP adapter]
    ERPAdapter <--> ERP[Business-owned stock / prices / orders]
    Services --> DB[(PostgreSQL business records / jobs / outbox)]
    Graph --> CP[(PostgreSQL workflow checkpoints)]
    DB --> Worker[Durable dispatch and scheduler]
    Worker --> Adapters
    Services --> Documents[Document rendering and private storage]
```
Adapters handle provider differences. Application services own transactions and use cases. Domain rules own financial calculations. The workflow coordinates steps. See [module contracts](module-boundaries.md).

## One approval service for all channels
```mermaid
flowchart LR
    E[Verified email reply] --> D[Common approval command]
    T[Verified messaging action] --> D
    P[Authenticated portal action] --> D
    D --> V[Check actor / tenant / quote version / expiry]
    V --> S[Atomically save decision / audit / resume job]
    S --> W[Worker resumes workflow]
```
Provider verification and actor enrollment occur before submitting a command; the service independently checks current permissions. Replayed/conflicting decisions cannot approve a different version.

## Deferred manager commands
```mermaid
flowchart TD
    A[Verified manager message] --> B{Enquiry or requested change?}
    B -- Stock enquiry --> C[Read ERP and return facts with timestamp]
    B -- Price or discount request --> D[Clarify target and scope; validate permissions]
    D --> E[Calculate revised draft]
    E --> F[Manager approves exact revision]
    F --> G[Existing approved quotation delivery]
```
This last flow and negotiation are M11 features. Global catalogue changes require explicit separate scope and capability decisions.
