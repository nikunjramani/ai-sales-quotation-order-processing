# Plan: follow-up messages continue the customer's open enquiry
**Status:** superseded by phase 4 (D22): built once on the contact and conversation model, see [conversations](../features/conversations.md) and [ADR 0021](../adr/0021-customers-conversations-and-website-chat.md). Kept for the history of the agreed rules.

## Context
In the demo the customer asked "can you get cables price?", and the system asked "How many metre of 2-core power cable do you need?". The customer answered "10 meter?". That answer became a **new** enquiry with no product, so the system asked again. Today one enquiry means one message, everywhere: the `enquiries.text` column, one extraction run per enquiry, one-way status rules, and the portal preview.

## User decisions (2026-10-23)
| Topic | Decision |
|---|---|
| Follow-ups | Linked to the customer's open enquiry (confirmed after a contradictory first answer) |
| Same customer | Same API key **and** the same `customer_reference` |
| How long it stays open | Until answered, **at most 7 days** |
| A different topic while a question is open | Added to the same enquiry (e.g. cables, then "also 2 pumps", gives one quotation) |

## Proposed rules (confirm or correct)
1. **Which enquiry a message joins:**
   - A new message joins an enquiry only when that enquiry is waiting in `needs_clarification`.
   - The enquiry must have the same tenant, the same API key subject and the same non-empty `customer_reference`.
   - Our last question must be less than 7 days old.
   - If several enquiries qualify, the newest one wins.
2. **Otherwise a new enquiry** is created, for example:
   - no `customer_reference`;
   - a different API key;
   - the enquiry is in review, being quoted or already quoted;
   - more than 7 days have passed.
3. **Review cases are never reopened.** Enquiries in `needs_review` (staff are looking) and anything with a quotation are never reopened by a customer message.
4. **The whole conversation is read again.**
   - The AI reads every message of the enquiry in order, e.g. "cables price?" + "10 meter?" gives 10 m cable.
   - The verbatim check accepts quotes from any of the messages.
5. **API answer:** 202 with the **existing** `enquiry_id` and `continued: true`. Idempotency stays per message (the same `Idempotency-Key` replays).
6. **Attachments** on a follow-up go through the same quarantine and inspection before the enquiry is read again.

## Design (generic: works for API now, email/Telegram later via their verified sender)
- **Migration 0008:**
  - New table `enquiry_messages` (append-only, tenant RLS): `id, tenant_id, enquiry_id, inbox_event_id (unique), text, received_at`.
  - Backfill: one message per existing enquiry.
  - `enquiries.text` keeps the first message, for compatibility.
  - The API role gets column-level `UPDATE (status, updated_at)` on `enquiries`, only for the `needs_clarification → received` reopening.
  - `workflow_runs` gains `round` (default 1); the unique key becomes (tenant, enquiry, graph_version, round), so each new message gets a fresh extraction run while finished runs stay as history.
- **Intake** (`application/intake.py`, `persistence/intake.py`), in one transaction:
  1. Store the inbox event as today.
  2. Find the open enquiry `FOR UPDATE`, using rule 1.
  3. Either append the message, set status `received` and queue `PREPARE_ENQUIRY`; or create a new enquiry as today.
  - A concurrent second message cannot open two runs, because of the row lock.
- **Workflow** (`workflows/enquiry.py`, `persistence/workflow.py`):
  - `enquiry_content` returns all messages in order.
  - The extract job payload carries the round number.
  - Readers already take the latest run.
- **Portal and API views:**
  - The enquiry list preview shows the latest message.
  - The quotation detail shows the whole conversation.
  - The customer `GET` adds `messages_count`.
- **Demo page:** shows a continued message under the same enquiry, using the `continued` flag.

## Tests
- **Unit:** the linking rules (each "otherwise new" case above); 7-day boundary; same reference but another key; needs_review not reopened; replay of a follow-up; combined text read by the workflow; second round runs while the first is kept.
- **PostgreSQL:** the migration with backfill and a downgrade cycle; append-only messages; RLS; the API role can change only status/updated_at; two concurrent follow-ups give one extraction.
- **Evaluation:** conversation cases, e.g. "cables price?" + "10 meter?" gives 10 m cable (rules and Gemini).
- **Live demo:** the transcript from 2026-10-23 ends in a quotation without repeating the product.

## Not in scope
- Sending questions by email or Telegram (M7).
- Staff answering in the portal.
- Merging enquiries by hand.

## Workflow
Changes stay local until the user gives permission to commit, push or open a PR (AGENTS.md).
