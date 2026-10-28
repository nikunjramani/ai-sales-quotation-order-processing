import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiKeysPage } from "@/features/business/ui/pages/ApiKeysPage";

import {
  jsonResponse,
  renderWithProviders,
  testQueryClient,
  TEST_SESSION,
} from "../../../../support/renderWithProviders";

const TOKEN = "qk_0123456789abcdef0123456789abcdef_secret-part";

describe("ApiKeysPage", () => {
  it("shows a new key once and keeps it out of every cache", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) =>
        Promise.resolve(
          init?.method === "POST"
            ? jsonResponse(201, { key_id: "k1", token: TOKEN })
            : jsonResponse(200, []),
        ),
      ),
    );
    const client = testQueryClient({
      ...TEST_SESSION,
      tenants: [{ ...TEST_SESSION.tenants[0]!, permissions: ["integrations:manage"] }],
    });
    renderWithProviders(<ApiKeysPage />, { client });
    await userEvent.type(await screen.findByLabelText("What is the key for?"), "Website");
    await userEvent.click(screen.getByRole("button", { name: "Create key" }));
    expect(await screen.findByText(TOKEN)).toBeTruthy();
    const cached = JSON.stringify(client.getQueryCache().getAll().map((query) => query.state.data));
    expect(cached).not.toContain(TOKEN);
    await userEvent.click(screen.getByRole("button", { name: "I have stored it" }));
    expect(screen.queryByText(TOKEN)).toBeNull();
  });
});
