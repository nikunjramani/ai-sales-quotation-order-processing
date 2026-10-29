import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Session } from "@/features/auth";
import type { Connection } from "@/features/connections/model/types";
import { OneClickToolsCard } from "@/features/connections/ui/components/OneClickToolsCard";
import { PendingActionPanel } from "@/features/connections/ui/components/PendingActionPanel";

import {
  jsonResponse,
  renderWithProviders,
  TEST_SESSION,
  testQueryClient,
} from "../../../../support/renderWithProviders";

const ADMIN: Session = {
  ...TEST_SESSION,
  tenants: [
    {
      ...TEST_SESSION.tenants[0]!,
      roles: ["administrator"],
      permissions: ["integrations:manage", "quotations:view"],
    },
  ],
};

const PAID_TOOL = {
  provider_key: "future_tool",
  provider_name: "Future tool",
  kind: "one_click",
  purposes: ["customer_messages"],
  free: false,
  cost_note: "About $1 a month",
};

const STARTED: Connection = {
  connection_id: "c9",
  provider_key: "future_tool",
  provider_name: "Future tool",
  display_name: "Future tool",
  purposes: ["customer_messages"],
  status: "setting_up",
  last_error: null,
  created_at: "2026-10-29T10:00:00Z",
  chat: null,
  pending: {
    action_id: "link",
    kind: "show_steps",
    title: "Connect your account",
    steps: ["Send /link AB12CD34EF to our bot"],
    url: null,
    form_schema: null,
    expires_at: null,
    once: { code: "AB12CD34EF" },
  },
};

describe("OneClickToolsCard", () => {
  it("shows a tool the portal has never heard of, and needs the cost tick", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, [PAID_TOOL]))
      .mockResolvedValue(jsonResponse(200, { connection: STARTED, pending: STARTED.pending, detail: null }));
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<OneClickToolsCard connections={[]} />, {
      client: testQueryClient(ADMIN),
    });

    await userEvent.click(await screen.findByRole("button", { name: "Enable" }));
    const enable = screen.getByRole("button", { name: "Enable Future tool" });
    expect((enable as HTMLButtonElement).disabled).toBe(true);
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(enable);

    const [url, init] = fetch.mock.calls[1]!;
    expect(url).toBe("/api/v1/tenants/t1/connections/enable");
    expect(JSON.parse(String(init.body))).toEqual({ provider_key: "future_tool", accept_costs: true });
  });
});

describe("PendingActionPanel", () => {
  it("shows the steps with the one-time code", () => {
    renderWithProviders(<PendingActionPanel connection={STARTED} />, {
      client: testQueryClient(ADMIN),
    });
    expect(screen.getByText("Send /link AB12CD34EF to our bot")).toBeTruthy();
    expect(screen.getByText("AB12CD34EF")).toBeTruthy();
  });

  it("sends a form's answers to the step, with secret fields as password inputs", async () => {
    const fetch = vi.fn().mockResolvedValue(
      jsonResponse(200, { connection: { ...STARTED, pending: null }, pending: null, detail: "Ready" }),
    );
    vi.stubGlobal("fetch", fetch);
    const form: Connection = {
      ...STARTED,
      pending: {
        ...STARTED.pending!,
        action_id: "register",
        kind: "fill_form",
        title: "Register",
        steps: [],
        once: {},
        form_schema: {
          required: ["legal_name"],
          properties: {
            legal_name: { type: "string", title: "Legal name" },
            tax_id: { type: "string", title: "Tax ID", writeOnly: true },
          },
        },
      },
    };
    renderWithProviders(<PendingActionPanel connection={form} />, { client: testQueryClient(ADMIN) });

    expect(screen.getByLabelText("Tax ID").getAttribute("type")).toBe("password");
    await userEvent.type(screen.getByLabelText("Legal name"), "Acme Pvt Ltd");
    await userEvent.type(screen.getByLabelText("Tax ID"), "ABCDE1234F");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    const [url, init] = fetch.mock.calls[0]!;
    expect(url).toBe("/api/v1/tenants/t1/connections/c9/actions/register");
    expect(JSON.parse(String(init.body))).toEqual({
      submission: { legal_name: "Acme Pvt Ltd", tax_id: "ABCDE1234F" },
    });
  });
});
