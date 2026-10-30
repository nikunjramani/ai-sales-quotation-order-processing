# 0025: A friendly portal design: plain words, a simple menu, a Home page and page hints
**Date:** 2026-10-30. **Status:** accepted; implemented on `feat/portal-friendly-design`, verified with portal tests (no backend change). Extends ADR 0013 (separate React portal) and ADR 0014 (feature and layer structure).

## Context
The user asked for a portal that is easy enough for a 10-year-old. The portal had a row of 7-8 text links, no start page, technical words ("Enquiries", "Connections", "Revision requested", raw role codes), no help on what a page is for, and hard-coded colours that broke dark mode in chat bubbles.

## Decision (user answers, 2026-10-30)
| Question | Answer |
|---|---|
| Scope | New look, new menu, a Home page and a one-line hint on every main page. No backend or business-rule change. Busy pages are **not** reorganised in this change. |
| Menu | Sidebar with icons on wide screens (900px and up); on phones a bottom bar with Home, Quotes, Messages, Orders (those the role may open) and "More" for the rest. |
| Words | Plain words on screen only. URLs, API and code names stay. |
| Icons | The `lucide-react` package, pinned at 1.60.0 (10 days old at install, following the "no brand-new releases" rule used for pillow). |
| Home page | Count cards with one "Open" button, only for what the role may use; latest 5 messages; setup progress while setting up; "All done!" when every card is 0. |
| Style | "Friendly and clean": soft background, white rounded cards, one blue main colour, 17px base text, 48px touch targets, an icon on every status badge. Light and dark themes. |

Renames (on screen only):

| Before | After |
|---|---|
| Inbox / Quotations / Enquiries / Connections / Setup | Messages / Quotes / Customer requests / Apps & channels / Get started |
| Revision requested / Revision submitted / Cannot price | Needs changes / Changes sent / Price missing |
| Needs review / Needs clarification / Ready for quotation / Being read | Needs a person / Ask the customer / Ready to quote / Reading… |
| Request revision (button), Needs revision (tab) | Ask for changes, Needs changes |
| administrator / sales_operator / approver / viewer | Admin / Sales / Manager / View only |

Mechanics:
- **Home** is a new feature (`features/home`) at `#/home`, built only from the existing lists. It never asks for a list the role may not open (the list hooks gained an `enabled` option). A card shows "…" while loading, "?" on error, never a false 0. A full first page (50 rows) shows as "50+".
- **Start page:** `#/` opens Home, except that a business still setting up opens Get started for those who can finish it (unchanged rule).
- **Orders tab in the URL** (`?filter=attention`), like quotes and requests, so a Home card can open it.
- **Card wording (Claude, flagged to the user):** the user saw "Quotes waiting for your OK". It became "Quotes waiting for approval", because the list includes versions the person created, which they may not approve.

## Consequences
- First-time users see what needs them and one button to press; status no longer relies on colour alone.
- The portal JS bundle went over Vite's 500 kB warning (505 kB, 150 kB gzip). Code splitting is a possible later step.
- Detail pages (quotation, order, product, conversation) keep their structure. Reorganising them ("one main action first") is an open idea, not decided.

## Addendum: Settings and Integrations (user answers, 2026-10-30)
The settings tabs were links styled only as buttons, so they showed as plain squashed text; and the tools (Telegram, website chat, ERP) were on "Apps & channels", visible to administrators only, so people looked for them in Settings.

| Question | Answer |
|---|---|
| Where integrations live | Inside Settings, as an **Integrations** section. "Apps & channels" leaves the main menu; `#/connections` and `#/channels` redirect (administrators to Settings > Integrations, others to their profile). |
| Managers' own accounts | "My linked accounts" moved to the **profile page** (shown to approvers inside a business). |
| Layout | One settings frame (`app/layout/SettingsLayout.tsx`): sections listed on the left with icon, name and one line on wide screens; pill tabs on phones. Sections: Business, Pricing, People, Integrations, API keys, each shown only to the roles that may open it. |
| Tools not built yet | "Coming soon" cards (WhatsApp, Email, SMS), greyed out, no button. One list (`features/connections/services/comingSoon.ts`); a planned card disappears by itself once a provider with that key is installed. **WhatsApp itself is not built** (it needs its own provider package and a Meta Business account). |
| Many old connections | One card per kind of tool ("API: 6 active"); switched-off ones behind "Show switched off (n)". |

Also: the setup step "A way for customers to reach you" now opens Integrations (the server already counts website chat, Telegram or an API key).
