import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { SetupChecklist } from "@/features/business/model/types";
import { SetupPage } from "@/features/business/ui/pages/SetupPage";

import {
  jsonResponse,
  renderWithProviders,
  testQueryClient,
  TEST_SESSION,
} from "../../../../support/renderWithProviders";

const ADMIN = {
  ...TEST_SESSION,
  tenants: [
    {
      ...TEST_SESSION.tenants[0]!,
      status: "setting_up" as const,
      roles: ["administrator"],
      permissions: ["tenant:manage", "members:manage", "integrations:manage"],
    },
  ],
};

function checklist(done: boolean): SetupChecklist {
  return {
    status: "setting_up",
    can_go_live: done,
    items: [
      { key: "pricing", done: true, required: true },
      { key: "product_source", done: false, required: false },
      { key: "test_enquiry", done, required: true },
    ],
  };
}

describe("SetupPage", () => {
  it("keeps Go live disabled until every required step is done", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, checklist(false))));
    renderWithProviders(<SetupPage />, { client: testQueryClient(ADMIN) });
    const button = await screen.findByRole("button", { name: "Go live" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("1 step(s) left before Go live.")).toBeTruthy();
    expect(screen.getByText("Later")).toBeTruthy(); // products: shown, not required yet
  });

  it("shows what the server says is still missing", async () => {
    const fetch = vi.fn((url: string, init?: RequestInit) =>
      Promise.resolve(
        init?.method === "POST"
          ? jsonResponse(409, {
              detail: { message: "Finish the setup first", missing: ["test_enquiry"] },
            })
          : url === "/api/v1/auth/session"
            ? jsonResponse(200, ADMIN)
            : jsonResponse(200, checklist(true)),
      ),
    );
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<SetupPage />, { client: testQueryClient(ADMIN) });
    await userEvent.click(await screen.findByRole("button", { name: "Go live" }));
    expect(await screen.findByText("Still missing: A test enquiry")).toBeTruthy();
    expect(fetch.mock.calls.some(([url]) => url === "/api/v1/tenants/t1/go-live")).toBe(true);
  });
});
