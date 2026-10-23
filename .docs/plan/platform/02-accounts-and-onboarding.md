# 2. Accounts and onboarding
**Goal:** a manager signs up, creates their business, invites colleagues and finishes setup in the portal, without anyone running scripts.

## Concepts
| Term | Meaning |
|---|---|
| **User** | A person who signs in (new `users` table: id, identity subject, email, name, created). Today a person is only a `subject` string |
| **Business (tenant)** | Exists today. Gains: display name, country, time zone, logo, status (`setting_up`, `active`, `suspended`) |
| **Membership** | Exists today (user + business + role). One user can belong to several businesses |
| **Invitation** | New: email + role + expiry + single-use token; accepting creates the membership |
| **Owner** | Proposed: the user who created the business; always an administrator; cannot be removed by others |

## Roles (existing, kept)
`administrator` (business settings, members, connections, catalogue), `sales_operator` (revises quotations, withdraws), `approver` (approves), `viewer` (reads). A manager in a small business usually holds administrator **and** approver. Proposed new permissions, granted to `administrator`:
- `integrations:manage` for connecting and disconnecting tools;
- `catalogue:manage` for product data;
- `members:manage` for inviting and removing people.

They fit the existing permission map in `domain/tenancy.py`.

## Sign-up and login
- **Identity provider.** Login stays behind the existing `VerifiedIdentity` port (ADR 0013). The provider is configurable and generic (OIDC), the same approach as AI models.
- **The choice is yours** ([decision D1/D2](07-decisions-needed.md)). Options:
  - Google/Microsoft sign-in;
  - email and password, or a one-time email code;
  - a hosted service (Auth0, Clerk) or a free self-hosted one (Keycloak).
- **The dev login stays** for development only.

## Creating a business
- **Steps:**
  1. Signed in, with no business yet, the user goes to "Create your business".
  2. They enter the name, country, currency and tax rate (or "set later").
  3. The quotation validity (default 7 days) is set.
- **Database bootstrap:** the API's database role must not get broad insert rights on tenants. A narrow owner-defined function `create_business(user, name, ...)` creates the tenant, the owner's memberships and the default pricing policy in one transaction. The runtime role may call it and nothing more. This keeps the "least privilege" rule from ADR 0002.
- **Status starts as `setting_up`:** nothing is sent to customers until the manager presses "Go live" ([decision D3](07-decisions-needed.md)).

## Setup checklist (portal home until live)
1. **Business details:** currency, tax, validity, PDF details (letterhead, address, tax ID).
2. **Product data source:** see [05](05-product-data.md).
3. **Customer channels:** where customers can send enquiries; see [03](03-connectors.md).
4. **Approval:** who approves, and on which tools (the portal is always available).
5. **Test:** send a test enquiry through each connected tool and see it arrive.
6. **Go live.**

Each step is shown as done or missing. The checklist reads the real state, such as connections and catalogue counts, so it never drifts.

## Settings screens (new portal features)
| Screen | Contents | Permission |
|---|---|---|
| Business | Name, country, time zone, logo, PDF details | `tenant:manage` |
| Pricing | Currency, tax, rounding, validity days, price/stock freshness | `tenant:manage` |
| Members | List, invite, change role, remove (never the last administrator) | `members:manage` |
| Connections | See [03](03-connectors.md) | `integrations:manage` |
| Catalogue | See [05](05-product-data.md) | `catalogue:manage` |
| API keys | Create (shown once), revoke; replaces `scripts/create_api_key.py` | `integrations:manage` |

## Things that stay open ([07](07-decisions-needed.md))
- Who may sign up: anyone, or only invited businesses during the pilot (D3).
- Billing and plans: proposed out of scope for now (D4).
- Removing a business and deleting its data: retention rules (D17).
