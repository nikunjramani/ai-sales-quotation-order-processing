# Two-window demo
A simple page for demos, kept outside the main code on purpose (no portal structure, no tests).
Development only; it refuses to start when `QUOTATION_ENVIRONMENT=production`.

- **Left, customer:** type an enquiry and press Send. The reply shows what was understood, any
  clarification questions, and, once approved, the quotation with **Download PDF**, **Accept**
  and **Decline**.
- **Right, manager's phone:** the approval message (lines, totals, stock) with **Approve**,
  **Reject** and **Request revision**. Notices such as "the customer accepted" appear here too.

## Run
```powershell
docker compose up -d --wait
uv run python demo/run_demo.py      # migrations + seed, API (8000), worker, demo page (8001)
```
Open http://127.0.0.1:8001. Ctrl+C stops everything. The full portal still works for details.

## How it works
`server.py` is a small FastAPI app that calls the real API:
- Customer: creates one intake API key for the demo business on first use and keeps it in
  `var/demo/state.json` (git-ignored); the browser never sees it.
- Manager: links the account `demo-manager-phone` to `manager@industrial.example` (dev sign-in,
  linking code, signed enroll event), reads review messages from the simulated channel outbox
  and sends decisions as signed events.

**Clear windows** forgets the shown enquiries and messages (records stay in the database) and
creates a new key and link next time, e.g. after resetting the database.
"Request revision" needs a sales operator to change the quotation in the portal
(`sales@industrial.example`); the new version then arrives on the phone again.
