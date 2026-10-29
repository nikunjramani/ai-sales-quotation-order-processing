import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { ApproveLinkPage } from "@/features/approvals/ui/pages/ApproveLinkPage";

import {
  jsonResponse,
  renderWithProviders,
  testQueryClient,
} from "../../../../support/renderWithProviders";

const OPEN = {
  tenant_id: "t1",
  business_name: "Demo Industrial",
  quotation_id: "q1",
  number: "Q-1A2B3C4D",
  version: 2,
  state: "open",
  decided: null,
  expires_at: "2026-10-30T10:00:00Z",
  content_sha256: "a".repeat(64),
  customer_reference: "CUST-42",
  content: {
    lines: [
      {
        sku: "IND-FAN-450",
        description: "Fan",
        quantity: "2",
        unit: "pcs",
        unit_price: "100.00",
        line_total: "200.00",
        stock_status: "available",
      },
    ],
    subtotal: "200.00",
    tax: "36.00",
    total: "236.00",
    currency: "INR",
  },
};

function page(client = testQueryClient()) {
  return renderWithProviders(
    <Routes>
      <Route path="/approve/:token" element={<ApproveLinkPage />} />
    </Routes>,
    { client, path: "/approve/tok-1" },
  );
}

describe("ApproveLinkPage", () => {
  it("shows the exact version and decides with one click after sign-in", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, OPEN))
      .mockResolvedValueOnce(jsonResponse(200, { action: "approve", replayed: false }))
      .mockResolvedValue(jsonResponse(200, { ...OPEN, state: "decided", decided: "approve" }));
    vi.stubGlobal("fetch", fetch);
    page();

    expect(await screen.findByText(/total 236.00 INR/)).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Approve" }));

    expect(await screen.findByText("Q-1A2B3C4D version 2 approved.")).toBeTruthy();
    const [url, init] = fetch.mock.calls[1]!;
    expect(url).toBe("/api/v1/approval-links/tok-1/decision");
    const body = JSON.parse(String(init.body));
    expect([body.action, body.content_sha256]).toEqual(["approve", "a".repeat(64)]);
  });

  it("asks for a reason before rejecting", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, OPEN)));
    page();
    await userEvent.click(await screen.findByRole("button", { name: "Reject" }));
    expect(screen.getByLabelText("Reason")).toBeTruthy();
  });

  it("says when the link belongs to someone else", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(403, { detail: "This link is not for you" })),
    );
    page();
    expect(await screen.findByText("This link is not for you")).toBeTruthy();
  });

  it("asks a signed-out person to sign in first", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, {})));
    page(testQueryClient(null));
    expect(await screen.findByText("Sign in to see and decide this approval request.")).toBeTruthy();
  });
});
