import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ThreadMessage } from "@/features/conversations/model/types";
import { MessageThread } from "@/features/conversations/ui/components/MessageThread";

import {
  jsonResponse,
  renderWithProviders,
  TEST_SESSION,
  testQueryClient,
} from "../../../../support/renderWithProviders";

const FAILED: ThreadMessage = {
  seq: 2,
  direction: "outbound",
  author: "system",
  text: "Your quotation Q-1 is ready",
  at: "2026-10-29T10:00:00Z",
  enquiry_id: "e1",
  template_key: "quotation_ready",
  outbound_status: "failed",
  outbound_error: "The customer must message first",
  outbound_message_id: "m1",
  can_resend: true,
};

const OPERATOR = {
  ...TEST_SESSION,
  tenants: [
    { ...TEST_SESSION.tenants[0]!, roles: ["sales_operator"], permissions: ["messages:resend"] },
  ],
};

describe("MessageThread", () => {
  it("shows customer text as text, never as HTML", () => {
    const { container } = renderWithProviders(
      <MessageThread
        messages={[
          {
            seq: 1,
            direction: "inbound",
            author: "customer",
            text: "<img src=x onerror=alert(1)> 10 meter?",
            at: "2026-10-28T10:00:00Z",
            enquiry_id: "e1",
            template_key: null,
            outbound_status: null,
            outbound_error: null,
          },
        ]}
      />,
    );
    expect(screen.getByText("<img src=x onerror=alert(1)> 10 meter?")).toBeTruthy();
    expect(container.querySelector("img")).toBeNull();
  });

  it("lets sales operators send a failed customer message again", async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(201, { message_id: "m2" }));
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<MessageThread messages={[FAILED]} />, {
      client: testQueryClient(OPERATOR as typeof TEST_SESSION),
    });
    await userEvent.click(screen.getByRole("button", { name: "Send again" }));
    expect(fetch.mock.calls[0]?.[0]).toBe("/api/v1/tenants/t1/messages/m1/resend");
  });

  it("offers no resend to people without the permission", () => {
    renderWithProviders(<MessageThread messages={[FAILED]} />);
    expect(screen.queryByRole("button", { name: "Send again" })).toBeNull();
  });
});
