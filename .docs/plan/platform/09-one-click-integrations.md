# 9. One-click integrations: "Enable" and we set everything up
**User decision (2026-10-23):**
- A business signs up, sets up their business, and for each tool just presses **Enable**. We create every account the tool needs **for that business**.
- The aim is easy integration for every business. Messaging costs can later be part of our paid plan (billing is out of scope for now, D4).
- Each business still gets **its own accounts**; nothing is shared between businesses (D9).

## How it works for the business
Portal → **Connections** → a card per tool with an **Enable** switch. While we set it up, the card shows progress. When it's ready it shows how customers reach the business, e.g. "✅ WhatsApp ready: +91 xxxxx" or "✅ Chat link: chat.ourapp.com/acme". The same switch is used for customer enquiries, and managers can also link their own account for approvals ([03](03-connectors.md)).

## What "Enable" does per tool
| Tool | What we do automatically | What the business must still do (platform rules) | Fully automatic? |
|---|---|---|---|
| **Website chat** (ours) | Create their chat, a hosted chat page/link and the website snippet | Nothing; pasting the snippet on their site is optional | ✅ Yes |
| **Email** | Create their own address on our domain (e.g. `acme@chat.ourapp.com`) with inbound and outbound mail through the email provider | Nothing; they may forward their own mailbox to it | ✅ Yes |
| **WhatsApp** (through Twilio) | Create the business's Twilio subaccount, **buy their phone number**, verify it ourselves (the number is ours, so we receive the code), register it, set webhooks and message templates | **One Meta pop-up** (Embedded Signup): log in with Facebook and confirm the business name. Meta reviews the display name against the real business name | ⚠️ All but one pop-up |
| **SMS** (through Twilio) | Buy a number in their country | Where the law requires registration (e.g. India DLT, USA 10DLC), they fill in business details in **our** form and we submit them | ✅ Mostly |
| **Instagram** | Connect through our Meta app; webhooks and messaging set up automatically | Log in once and choose their Instagram professional account; we cannot create it for them | ⚠️ One login |
| **Facebook Messenger** | Same as Instagram | Log in once and choose their Facebook page | ⚠️ One login |
| **Telegram** | Run the bot behind **their own Telegram account** (Telegram's "connected business bot" feature), so customers chat with the business's account | Switch it on once in Telegram's Business settings (we show the steps) | ⚠️ One step in Telegram |

### Why WhatsApp needs that one pop-up
- To avoid it, every business's number would have to live under **our** Meta account.
- Meta requires the display name to belong to the business that owns the account. So other businesses' names under our account would likely be refused, or risk our account being banned.
- It would also break D9 (no shared accounts).

So we automate everything else and ask for **one confirmation, once**.

## What we (the company) must set up once
These take weeks and need a registered company, so they should start early. None of them block phases 1-4.
| Task | Needed for | Notes |
|---|---|---|
| Meta business verification of our company | WhatsApp, Instagram, Messenger | Done once in Meta Business Manager |
| Join Meta's **Tech Provider** programme (through Twilio) | WhatsApp Enable flow | Twilio documents the programme for software vendors; one Twilio **subaccount per business** |
| Meta **App Review** for Instagram and Messenger messaging permissions (Advanced Access) | Instagram, Messenger | Needed because our app serves many businesses; about 2-4 weeks per a third-party estimate |
| Twilio account with SendGrid (email) | Email, WhatsApp, SMS | Twilio bills us, so costs can later go into our paid plan (to confirm with Twilio) |
| A domain for business email addresses and chat links (e.g. `ourapp.com`) | Email, website chat | DNS records for sending (SPF/DKIM) |
| Our Telegram bot | Telegram | Created once with BotFather; Business mode switched on |
| A public HTTPS address | All webhooks | Development: a tunnel; production: hosting (D24) |

## How this stays generic
- **"Enable" is one more provider operation, `provision(business)`, next to `setup`, `send`, `verify_inbound` ([03](03-connectors.md)).** It returns either "ready" or "needs the business to do X". X is an *action* the portal can show without provider-specific code:
  - open a pop-up URL (Meta);
  - show steps (Telegram);
  - fill in a form built from the provider's schema (SMS registration).
- **Disable mirrors Enable:** `deprovision(business)` releases the number, closes the address and removes webhooks, after a confirmation.
- **What we create is stored per business on the connection:** numbers, subaccount IDs and addresses. Secrets go in the cloud secret manager (D8), never in the portal.
- **A new tool later** is still one adapter package that implements `provision`; the Connections page shows its card automatically.

## Costs to keep in mind (paid plan later)
- **Phone numbers:** a monthly fee per number (WhatsApp/SMS).
- **Messages:** WhatsApp conversations are charged by Meta; SMS and email per message, depending on volume.
- **Free:** website chat, Telegram and Instagram/Messenger messaging.

## Sources (checked 2026-10-23)
[Twilio Tech Provider programme](https://www.twilio.com/docs/whatsapp/isv/tech-provider-program) · [Twilio: register senders (subaccount per customer)](https://www.twilio.com/docs/whatsapp/isv/register-senders) · [Meta Embedded Signup](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/overview/) · [Meta: onboarding customers as a Tech Provider](https://developers.facebook.com/documentation/business-messaging/whatsapp/embedded-signup/onboarding-customers-as-a-tech-provider) · [Instagram App Review](https://developers.facebook.com/docs/instagram-platform/app-review) · [Telegram connected business bots](https://core.telegram.org/api/bots/connected-business-bots) · [WhatsApp display name guidelines (360dialog)](https://docs.360dialog.com/whatsapp-display-name-guidelines)
