import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Connection } from "@/features/connections/model/types";
import { ConnectionList } from "@/features/connections/ui/components/ConnectionList";

import { renderWithProviders } from "../../../../support/renderWithProviders";

describe("ConnectionList", () => {
  it("shows each tool with its status, purposes and (for administrators) its last error", () => {
    const connections: Connection[] = [
      {
        connection_id: "c1",
        provider_key: "api",
        provider_name: "API (customer systems)",
        display_name: "Website",
        purposes: ["customer_messages"],
        status: "active",
        last_error: null,
        created_at: "2026-10-27T10:00:00Z",
      },
      {
        connection_id: "c2",
        provider_key: "simulated",
        provider_name: "Simulated phone",
        display_name: "Shop phone",
        purposes: ["manager_approvals"],
        status: "error",
        last_error: "signature key rotated",
        created_at: "2026-10-27T10:00:00Z",
      },
    ];
    renderWithProviders(<ConnectionList connections={connections} />);
    expect(screen.getByText("Website")).toBeTruthy();
    expect(screen.getByText("Active")).toBeTruthy();
    expect(screen.getByText("Needs attention")).toBeTruthy();
    expect(
      screen.getByText(/Simulated phone · Manager approvals/),
    ).toBeTruthy();
    expect(screen.getByText("Last error: signature key rotated")).toBeTruthy();
  });
});
