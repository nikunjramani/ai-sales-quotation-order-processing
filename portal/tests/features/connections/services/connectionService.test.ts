import { describe, expect, it } from "vitest";

import type { Connection } from "@/features/connections/model/types";
import {
  canLink,
  purposeText,
} from "@/features/connections/services/connectionService";

const PHONE: Connection = {
  connection_id: "c1",
  provider_key: "simulated",
  provider_name: "Simulated phone",
  display_name: "Shop phone",
  purposes: ["manager_approvals", "catalogue"],
  status: "active",
  last_error: null,
  created_at: "2026-10-27T10:00:00Z",
};

describe("connectionService", () => {
  it("lets managers link only active approval connections, whatever the provider", () => {
    expect(canLink(PHONE)).toBe(true);
    expect(canLink({ ...PHONE, provider_key: "telegram" })).toBe(true);
    expect(canLink({ ...PHONE, status: "disabled" })).toBe(false);
    expect(canLink({ ...PHONE, purposes: ["customer_messages"] })).toBe(false);
  });

  it("describes purposes in plain words", () => {
    expect(purposeText(PHONE)).toBe("Manager approvals, Product data");
  });
});
