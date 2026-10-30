# Portal architecture (React)
The portal is organised **by feature**, and each feature is split into **layers**. UI, state, business rules and HTTP calls live in separate files. Adding a screen touches only its feature, and [tests/architecture.test.ts](../../portal/tests/architecture.test.ts) fails if the rules below are broken. Decision record: [ADR 0014](../adr/0014-portal-structure-and-state.md).

## Folder structure
```text
portal/src/
  main.tsx                    start-up: mounts <App/>, loads global styles
  app/                        the shell: wires features together, owns no business logic
    App.tsx                   providers (TanStack Query, router)
    router.tsx                route table = routes exported by each feature
    queryClient.ts            cache and retry policy for server state
    layout/                   AppLayout (session + tenant gate), TopBar, SideNav/BottomNav, navigation.ts (the menu), SettingsLayout + settingsNavigation.ts (the settings frame), NotFoundPage
  shared/                     reusable code with no feature knowledge
    api/httpClient.ts         the only fetch: CSRF header, ApiError, query strings
    lib/                      pure helpers (format, commandId)
    ui/                       generic components (PageHeader, StatusBadge/ToneBadge, FilterTabs, QueryState)
  features/
    <feature>/
      model/                  types only (API shapes, form shapes)
      api/                    repository: HTTP calls for this feature, nothing else
      services/               pure rules: validation, filters, payload building (no React, no HTTP)
      store/                  client state with Zustand (only if the feature needs it)
      hooks/                  state and behaviour: TanStack queries and mutations, form hooks
      ui/pages/               screens (one per route); read hooks, render components
      ui/components/          pieces of screens; render props and call hooks
      routes.tsx              this feature's routes
      index.ts                public API: the only file other features or the app may import
  styles/global.css           design tokens (light/dark), shell, components (ADR 0025)
portal/tests/                 mirrors src/ (no test files inside src/)
```

Current features:

| Feature | Purpose |
|---|---|
| `auth` | Session state (with the person and each business's status), route guard |
| `account` | Sign-up, password and dev login, email links, profile, accepting invitations (phase 2) |
| `business` | Create a business, setup checklist and Go live, settings, pricing, people, API keys (phase 2) |
| `tenant` | Selected business (Zustand), permission helper, switcher |
| `home` | The start page (ADR 0025): to-do count cards per permission, latest messages, setup progress; built from other features' list hooks |
| `quotations` | List, review, decide, revise |
| `enquiries` | Exception list |
| `connections` | Settings > Integrations (connected tools grouped by kind, one-click tools, website chat, Coming soon) and the managers' linked accounts on the profile page; `#/connections` and `#/channels` redirect (ADR 0025) |
| `catalogue` | The business's own product list (phase 3): products with search and paging, product page (details, prices, stock, archive, changes), categories. Filters in a Zustand store read through a hook; prices and quantities shown exactly as sent |

## Layers and who may import whom
Within a feature:

| Layer | May import | Must not |
|---|---|---|
| model | model | anything with behaviour |
| api (repository) | model, `shared/api` | React, Query, Zustand, router |
| services | model, `shared/lib` | React, Query, Zustand, router, HTTP |
| store | model | HTTP |
| hooks | api, services, store, model | ui |
| ui | hooks, services, model, `shared/ui` | api (go through hooks) |
| routes | ui | |
| index | anything in the feature | |

Across code areas:
- **Features:** a feature may use another feature only through its `index.ts` (e.g. `@/features/tenant`). It never reaches into that feature's folders.
- **shared:** never imports features or app.
- **Features and the app:** features never import the app.
- **HTTP:** only `shared/api/httpClient.ts` calls `fetch`.

Imports use the `@/` alias for `src/` (`@/shared/ui/StatusBadge`). Inside a feature, relative paths are fine.

## State management
| Kind of state | Where | Example |
|---|---|---|
| Server state (data from the API) | TanStack Query in `hooks/`, keys in `queryKeys` per feature, always including the tenant ID | Quotation list and detail, session, bindings |
| Client state shared across screens | Zustand store in `store/` | Selected business (remembered in localStorage) |
| URL state | Router search params | `?filter=revision` on lists |
| Form / local state | A form hook in `hooks/` (e.g. `useDecisionForm`) | Reason text, edited lines, retry command IDs |

**Rules:**
- Server data is never copied into Zustand or `useState`. Mutations invalidate the matching query keys instead. For example, a decision refreshes `["tenants", t, "quotations"]`.
- 4xx responses are not retried. Mutations are never retried automatically: a person retries them, and the form hook reuses the same command ID, so the server applies the action once.
- **Logout** clears the whole cache. **Switching business** remounts pages, and every cache key includes the tenant, so nothing leaks between businesses.
- Permissions in the UI (`can(...)`, `can_decide`) only show or hide controls. The server checks every action.

## How to add things
**A screen to an existing feature** (e.g. "quotation compare"):
1. Add types to `model/` and any endpoint to `api/<feature>Repository.ts`.
2. Put rules (validation, mapping) in `services/`, then add a query or mutation hook in `hooks/`.
3. Add the page in `ui/pages/` and its parts in `ui/components/`.
4. Add the route in the feature's `routes.tsx`. The app router picks it up automatically.
5. Add tests in `portal/tests/features/<feature>/...`, mirroring the source path.

**A new feature** (e.g. `orders`): create `features/orders/` with the layers it needs plus `index.ts` and `routes.tsx`. Add one line to `app/router.tsx`, and an entry (label, icon, permissions, `primary` for the phone bar) in `app/layout/navigation.ts` if it needs a menu item.

## Testing
- Tests mirror `src/` under `portal/tests/`.
- Shared helpers live in `tests/support/`: `renderWithProviders` gives a test the same providers and a signed-in session.
- Pure services get plain unit tests. Components are tested through what the user sees and what is sent to the API (`fetch` is stubbed).
- `tests/architecture.test.ts` enforces this document.
- Commands, from `portal/`: `npm run typecheck`, `npm test` and `npm run build`.

## Website chat widget (phase 4)
`src/widget/` is a separate customer-side app (plain TypeScript, Shadow DOM, no React) built by `vite.widget.config.ts`. The architecture test keeps it apart: it may not import portal code and the portal may not import it; only `widget/api/chatClient.ts` calls `fetch` and only `widget/state/` uses browser storage (the visitor's own chat token).

## Design and wording (ADR 0025)
- **Every main page starts with `PageHeader`** (`shared/ui/PageHeader.tsx`): an icon, the title and a one-sentence `hint` saying what the page is for. Put page buttons in `actions`.
- **Plain words on screen.** Use the names in ADR 0025 (Quotes, Customer requests, Messages, Apps & channels, Get started; Manager, Sales, Admin, View only). Codes, URLs and API names stay technical.
- **Status = colour + icon + words.** Use `StatusBadge` (shared statuses) or `ToneBadge` (feature-specific words); never colour alone.
- **Colours come from the tokens** in `global.css`, never hex values in components, so dark mode keeps working.
- **Touch targets are at least 48px** (buttons, inputs, menu items); icons from `lucide-react` are decorative (`aria-hidden`) next to a visible word.
- **Lists that Home links to keep their filter in the URL** (`?filter=`).
- **A new settings section:** add an entry to `app/layout/settingsNavigation.ts` and export its route (a relative path such as `"integrations"`) from the feature's `...SettingsRoutes`; `app/router.tsx` mounts those under `/settings` inside `SettingsLayout`. The page renders only its content (no page header or tabs of its own).
- **A planned tool:** add it to `features/connections/services/comingSoon.ts`; it is hidden automatically once its provider is installed.
