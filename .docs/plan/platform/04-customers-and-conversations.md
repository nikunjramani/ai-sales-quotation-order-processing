# 4. Customers and conversations
**Goal:** a customer can write on any connected tool, and the system recognises them and keeps the conversation together. "10 meter?" then answers the previous question. Questions and quotations go back on the same tool.

## Concepts
| Term | Meaning |
|---|---|
| **Contact** | A customer of one business (name, company, notes). New table `contacts` |
| **Contact identity** | How we recognise that customer on one connection: (connection, external ID) such as a Telegram chat ID, WhatsApp number, email address, web-chat visitor or API `customer_reference`. Plus whether it is **verified** by the provider, and consent state. One contact can have several identities |
| **Conversation** | The message thread with one contact on one connection (new table `conversations`) |
| **Message** | Every inbound and outbound message, append-only (new `conversation_messages`; outbound ones reference `outbound_messages`) |
| **Enquiry** | Exists today. Gains `conversation_id`; its text becomes the conversation messages that belong to it |

## How an inbound customer message is handled
1. The connector produces a `CustomerMessage` event ([03](03-connectors.md)).
2. **Find or create the contact identity** for (connection, sender). Identities are never merged across tools automatically; staff can merge contacts by hand, or a verified email/phone match can suggest it (D13).
3. **Find or create the conversation.**
4. **Decide what the message is for**, through a small *intent* step that is generic and extendable:
   - **follow-up** to an enquiry that is waiting for the customer's answer;
   - **new enquiry**;
   - later: **order status**, **payment**, **talk to a person**.

   In the first version, a message is a follow-up when the contact has an enquiry waiting in `needs_clarification` from the last 7 days (the rules already agreed in [conversation-follow-ups](../conversation-follow-ups.md)). Otherwise it is a new enquiry. Later intents plug in as handlers without changing this step.
5. **Follow-up:** the message is added to the enquiry and the whole conversation is read again. One enquiry leads to one quotation.
6. Outbound replies (questions, the quotation, confirmations) are created as `outbound_messages` to the same identity and connection.

This **replaces** the "API key + `customer_reference`" rule in the earlier follow-up plan with the general contact model. For the API provider, an identity is (API connection, `customer_reference`), so API behaviour matches what was agreed.

## Sending things back to the customer (new)
| What | When | Content (fixed template) |
|---|---|---|
| Acknowledgement | Optional, on receipt (D14) | "Thanks, we are preparing your quotation." |
| Clarification questions | Outcome `needs_clarification` | The existing questions (category lists, "how many…") |
| Quotation | After approval and PDF | Summary, total, valid until, PDF (attachment or link), accept/decline actions |
| Answer confirmation | After accept/decline | "Thank you, we received your acceptance." |
| Later: order and payment updates | See [06](06-future-commerce.md) | Status templates |

## Customer acceptance over chat (needs your decision, D11)
ADR 0016 allows answers only through the API, bound to version and content hash. For chat tools there are three options:
- **Recommended:** buttons or signed links carrying a single-use reference bound to the version, hash and identity, the same security as manager actions.
- Accept a typed "yes" only from a **verified** identity. This is riskier: ambiguous text, forwarded messages.
- Links that open a small page showing the quotation, with Accept/Decline.

## Consent and opt-out
- Customers who write first have started the conversation.
- "STOP"/unsubscribe events set the identity's consent to `opted_out`, and nothing more is sent.
- Some tools (WhatsApp) require templates for business-initiated messages; capabilities enforce this ([03](03-connectors.md)).
- The policy text and the retention period are business and legal decisions (D15, D17).

## Portal
- **Inbox:** conversations with the latest message, the linked enquiry or quotation status and the tool icon. Staff can read the whole thread.
- **Contacts:** a list and a detail page (identities, enquiries, quotations).
- **Optional:** staff typing replies manually from the portal (D16; not in the first version).
