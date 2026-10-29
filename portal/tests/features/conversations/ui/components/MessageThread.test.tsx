import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageThread } from "@/features/conversations/ui/components/MessageThread";

import { renderWithProviders } from "../../../../support/renderWithProviders";

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
});
