import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Connection } from "@/features/connections/model/types";
import { LinkAccountCard } from "@/features/connections/ui/components/LinkAccountCard";

import {
  jsonResponse,
  renderWithProviders,
} from "../../../../support/renderWithProviders";

const PHONE: Connection = {
  connection_id: "c1",
  provider_key: "simulated",
  provider_name: "Simulated phone",
  display_name: "Shop phone",
  purposes: ["manager_approvals"],
  status: "active",
  last_error: null,
  created_at: "2026-10-27T10:00:00Z",
};

describe("LinkAccountCard", () => {
  it("offers one button per linkable connection and shows the one-time code", async () => {
    const fetch = vi.fn().mockResolvedValue(
      jsonResponse(201, {
        connection_id: "c1",
        channel: "simulated",
        code: "ABC123",
        expires_at: "2026-10-27T10:10:00Z",
      }),
    );
    vi.stubGlobal("fetch", fetch);
    const api = {
      ...PHONE,
      connection_id: "c2",
      display_name: "Website API",
      purposes: ["customer_messages" as const],
    };
    renderWithProviders(<LinkAccountCard connections={[PHONE, api]} />);

    expect(screen.queryByRole("button", { name: /Website API/ })).toBeNull();
    await userEvent.click(
      screen.getByRole("button", { name: "Link my account on Shop phone" }),
    );
    expect(await screen.findByText("ABC123")).toBeTruthy();
    expect(fetch.mock.calls[0]?.[0]).toBe(
      "/api/v1/tenants/t1/connections/c1/enrollments",
    );
  });

  it("says so when no tool for approvals is connected", () => {
    renderWithProviders(<LinkAccountCard connections={[]} />);
    expect(
      screen.getByText("No tool for approvals is connected yet."),
    ).toBeTruthy();
  });
});
