import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CustomerView } from "@/features/quotations/model/types";
import { CustomerPanel } from "@/features/quotations/ui/components/CustomerPanel";

import { jsonResponse, renderWithProviders } from "../../../../support/renderWithProviders";

const OPEN: CustomerView = {
  offered_version: 1,
  customer_status: "open",
  valid_until: "2026-10-30T10:00:00Z",
  issued_at: "2026-10-23T10:00:00Z",
  responses: [],
  can_withdraw: true,
};

describe("CustomerPanel", () => {
  it("shows what the customer holds and withdraws with a reason, reusing the command ID", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, OPEN))
      .mockResolvedValueOnce(jsonResponse(503, { detail: "down" }))
      .mockResolvedValue(jsonResponse(200, OPEN));
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<CustomerPanel quotationId="q1" />);

    expect(await screen.findByText("Waiting for the customer")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Withdraw" }));
    expect((await screen.findByRole("alert")).textContent).toContain("reason");
    expect(fetch).toHaveBeenCalledTimes(1); // nothing sent without a reason

    await userEvent.type(screen.getByLabelText(/Withdraw this quotation/), "Wrong product");
    await userEvent.click(screen.getByRole("button", { name: "Withdraw" }));
    expect((await screen.findByRole("alert")).textContent).toContain("down");
    await userEvent.click(screen.getByRole("button", { name: "Withdraw" }));
    await waitFor(() => expect(fetch.mock.calls.length).toBeGreaterThanOrEqual(3));

    const posts = fetch.mock.calls.filter(([, init]) => (init as RequestInit).method === "POST");
    const [first, second] = posts.map(([, init]) => JSON.parse(String((init as RequestInit).body)));
    expect(posts[0]?.[0]).toBe("/api/v1/tenants/t1/quotations/q1/withdrawal");
    expect(first.reason).toBe("Wrong product");
    expect(second.command_id).toBe(first.command_id);
  });

  it("lists answers, including why an acceptance was refused, without a withdraw button", async () => {
    const answered: CustomerView = {
      ...OPEN,
      customer_status: "being_revised",
      can_withdraw: false,
      responses: [
        {
          response_id: "r1",
          version: 1,
          outcome: "refused_changed",
          actor: "api-key:1",
          reason: null,
          differences: ["IND-FAN-450 unit_price 4250.00 -> 4500.00"],
          revised_version: 2,
          created_at: "2026-10-24T09:00:00Z",
        },
      ],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, answered)));
    renderWithProviders(<CustomerPanel quotationId="q1" />);

    expect(await screen.findByText("Being revised (prices changed)")).toBeTruthy();
    expect(screen.getByText("IND-FAN-450 unit_price 4250.00 -> 4500.00")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Withdraw" })).toBeNull();
  });
});
