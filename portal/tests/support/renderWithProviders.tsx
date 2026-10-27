// Test helper (not a mirror of src): renders UI inside the same providers the app uses, with an
// optional signed-in session already in the cache.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, renderHook } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter } from "react-router";

import type { Session } from "@/features/auth";

export const TEST_SESSION: Session = {
  subject: "manager@industrial.example",
  provider: "dev",
  expires_at: "2026-10-23T18:00:00Z",
  csrf_token: "csrf-test",
  user: null,
  tenants: [
    {
      tenant_id: "t1",
      name: "Demo Industrial",
      status: "active",
      roles: ["approver"],
      permissions: ["quotations:view", "quotations:approve", "enquiries:view"],
    },
  ],
};

export function testQueryClient(session: Session | null = TEST_SESSION): QueryClient {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  client.setQueryData(["auth", "session"], session);
  return client;
}

function wrapper(client: QueryClient, path: string) {
  return function Providers({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

export function renderWithProviders(
  ui: ReactElement,
  { client = testQueryClient(), path = "/" }: { client?: QueryClient; path?: string } = {},
) {
  return { client, ...render(ui, { wrapper: wrapper(client, path) }) };
}

export function renderHookWithProviders<T>(
  hook: () => T,
  { client = testQueryClient() }: { client?: QueryClient } = {},
) {
  return { client, ...renderHook(hook, { wrapper: wrapper(client, "/") }) };
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}
