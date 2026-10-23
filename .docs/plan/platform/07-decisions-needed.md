# 7. Decisions needed from the user
Nothing below is decided. Each decision lists options and a recommendation with its reason. **Blocking for** names the phase ([08](08-phases.md)) that cannot start without it.

## Accounts and onboarding
| # | Question | Options | Recommendation | Blocking for |
|---|---|---|---|---|
| D1 | How do managers sign in? | (a) Google/Microsoft sign-in; (b) email + password; (c) one-time email code; (d) several | (a) + (c). No passwords to store; works for small businesses | Phase 2 |
| D2 | Which identity service? | (a) Keycloak, free and self-hosted, more to run; (b) Auth0/Clerk, hosted, free tier then paid; (c) build email-code login ourselves | (a) for control and no cost, or (b) for speed. Behind the existing port either way | Phase 2 |
| D3 | Who may create a business? | (a) Anyone (self-service); (b) only with an invitation from us during the pilot | (b) for the pilot, then (a). Avoids spam and costs on paid tools | Phase 2 |
| D4 | Billing and plans? | (a) Out of scope now; (b) plan limits now | (a) | — |

## Connectors
| # | Question | Options | Recommendation | Blocking for |
|---|---|---|---|---|
| D5 | Which tools first, in order? | Website chat, Telegram, email, WhatsApp, Instagram, SMS | 1) website chat (free, ours); 2) Telegram (free, no review); 3) email; 4) WhatsApp; 5) Instagram | Phase 4-5 |
| D6 | WhatsApp: Meta directly or through a provider (Twilio, Gupshup, 360dialog)? | Direct is cheaper but needs Meta verification; a provider is quicker to start but costs per message | Decide when WhatsApp is next; the adapter model supports both | Phase 5 |
| D7 | Email: which sending/receiving service? | Postmark, SendGrid, Mailgun, Amazon SES, or a business's own mailbox over IMAP | One webhook-based service first (free tier); IMAP later | Phase 5 |
| D8 | Where are tool secrets kept? | (a) Encrypted in our database with a master key from the environment; (b) a cloud secret manager | (a) now (free), with the master key moving to a cloud key service in production | Phase 1 |
| D9 | Can several businesses share one platform bot/number, or must each connect its own? | (a) Each business its own account; (b) a shared platform account for small businesses | (a). Clear ownership, simpler isolation | Phase 3 |
| D10 | Manager approval by replying to an email: what counts as proof? (open since M5) | Provider-verified DKIM/DMARC plus a reply-to token; or signed links only | Signed links first; email reply later with D10 settled | Phase 5 (email approval) |

## Customers and conversations
| # | Question | Options | Recommendation | Blocking for |
|---|---|---|---|---|
| D11 | How does a customer accept a quotation in chat? | (a) Buttons or signed links (single-use, bound to version); (b) typed "yes" from a verified identity; (c) link to a small quotation page | (a), with (c) where buttons don't exist | Phase 4 |
| D12 | Website chat: must visitors give an email or phone? | (a) Anonymous allowed; (b) email or phone required; (c) verified by a one-time code | (b) at least, so quotations can reach them again; (c) optional per business | Phase 4 |
| D13 | Same person on two tools: merge automatically? | (a) Never automatically, staff merge; (b) suggest when a verified email/phone matches | (a) + (b) suggestions | Phase 4 |
| D14 | Send an "we got your enquiry" acknowledgement? | Yes / no / per business | Per business, default on | Phase 4 |
| D15 | Consent and opt-out wording, STOP handling | Business-provided text; platform default | Platform default plus a per-business override; STOP always honoured | Phase 4 |
| D16 | Can staff type manual replies to customers in the portal? | Not now / yes | Not in the first version (keeps answers template-only); later as a human handoff | — |
| D17 | How long do we keep conversations and files? | e.g. 1 / 2 / 7 years, or per business | Needs a legal view for the pilot country | Before real data |

## Product data
| # | Question | Options | Recommendation | Blocking for |
|---|---|---|---|---|
| D18 | Which product sources first? | Spreadsheet import, manual entry, ERP connector (which system?), shop connector | Spreadsheet + manual first (works for everyone); then the pilot business's real system | Phase 3 |
| D19 | Amend ADR 0003 so we may hold a business's catalogue when they choose it? | Yes / no | Yes. The ERP stays authoritative when connected | Phase 3 |
| D20 | Product synonyms per business? | Now / later | Later; start with full-text and similarity search | — |
| D21 | Which ERP or shop systems do target businesses use? | Tally, Zoho, Odoo, ERPNext, SAP B1, Shopify, WooCommerce... | Ask 2-3 pilot businesses; build the first one they use | Phase 6 |

## Sequencing
| # | Question | Options | Recommendation |
|---|---|---|---|
| D22 | The follow-up messages feature planned earlier (API key + customer reference): build it now, or as part of the conversation model (phase 4)? | Now (small, API only) / with phase 4 | With phase 4, so it is built once on the general contact model |
| D23 | Where does this sit against the roadmap (M6b orders, M7 integrations)? | Platform phases first, then orders; or orders first | Platform phases replace and extend M7; orders (M6b) after phase 4 |
| D24 | Hosting for real webhooks (providers need a public HTTPS address) | A cloud host; a tunnel (ngrok/Cloudflare) for development | Tunnel for development now; hosting decided before the pilot (M8) |
