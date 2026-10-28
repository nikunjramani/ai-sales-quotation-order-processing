import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LoginPage } from "@/features/account/ui/pages/LoginPage";

import {
  jsonResponse,
  renderWithProviders,
  testQueryClient,
  TEST_SESSION,
} from "../../../../support/renderWithProviders";

function server(config: { dev_login: boolean }, login: Response) {
  return vi.fn((url: string) =>
    Promise.resolve(
      url === "/api/v1/auth/config"
        ? jsonResponse(200, { password_login: true, ...config, dev_subjects: ["a@x.example"] })
        : login,
    ),
  );
}

describe("LoginPage", () => {
  it("offers the dev sign-in only when the server does", async () => {
    vi.stubGlobal("fetch", server({ dev_login: false }, jsonResponse(401, {})));
    renderWithProviders(<LoginPage />, { client: testQueryClient(null) });
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeTruthy();
    expect(screen.queryByText(/Development sign-in/)).toBeNull();
  });

  it("shows one generic message for every failure", async () => {
    vi.stubGlobal(
      "fetch",
      server({ dev_login: true }, jsonResponse(401, { detail: "Email or password is incorrect" })),
    );
    renderWithProviders(<LoginPage />, { client: testQueryClient(null) });
    expect(await screen.findByText(/Development sign-in/)).toBeTruthy();
    await userEvent.type(screen.getByLabelText("Email"), "ana@shop.example");
    await userEvent.type(screen.getByLabelText("Password"), "a long passphrase");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Email or password is incorrect.")).toBeTruthy();
  });

  it("stores the session the server returns", async () => {
    vi.stubGlobal("fetch", server({ dev_login: false }, jsonResponse(200, TEST_SESSION)));
    const client = testQueryClient(null);
    renderWithProviders(<LoginPage />, { client });
    await userEvent.type(await screen.findByLabelText("Email"), "ana@shop.example");
    await userEvent.type(screen.getByLabelText("Password"), "a long passphrase");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await vi.waitFor(() => expect(client.getQueryData(["auth", "session"])).toEqual(TEST_SESSION));
  });
});
