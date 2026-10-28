import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CHECK_EMAIL } from "@/features/account/services/links";
import { PROBLEM_TEXT } from "@/features/account/services/passwordRules";
import { SignupPage } from "@/features/account/ui/pages/SignupPage";

import {
  jsonResponse,
  renderWithProviders,
  testQueryClient,
} from "../../../../support/renderWithProviders";

async function fill(email: string, password: string) {
  await userEvent.type(screen.getByLabelText("Email"), email);
  await userEvent.type(screen.getByLabelText("Password"), password);
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));
}

describe("SignupPage", () => {
  it("always says to check the email, so nobody learns which addresses have accounts", async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(202, { status: "check_email" }));
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<SignupPage />, { client: testQueryClient(null) });
    await fill("ana@shop.example", "a long passphrase");
    expect(await screen.findByText(CHECK_EMAIL)).toBeTruthy();
    const [url, init] = fetch.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/auth/signup");
    expect(JSON.parse(String(init?.body))).toEqual({
      email: "ana@shop.example",
      password: "a long passphrase",
    });
  });

  it("hints the rules while typing and shows the server's reasons", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(422, { detail: { message: "x", problems: ["too_common"] } }),
      ),
    );
    renderWithProviders(<SignupPage />, { client: testQueryClient(null) });
    await userEvent.type(screen.getByLabelText("Password"), "short");
    expect(screen.getByText(PROBLEM_TEXT.too_short)).toBeTruthy();
    await userEvent.clear(screen.getByLabelText("Password"));
    await fill("ana@shop.example", "password1234");
    expect(await screen.findByText(PROBLEM_TEXT.too_common)).toBeTruthy();
  });
});
