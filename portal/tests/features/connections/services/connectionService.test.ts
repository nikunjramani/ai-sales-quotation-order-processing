import { describe, expect, it } from "vitest";

import type { Connection } from "@/features/connections/model/types";
import {
  canLink,
  formDefaults,
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
  chat: null,
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

  it("prefills setup forms from their schema defaults, never secret fields", () => {
    const schema = {
      properties: {
        sync_minutes: { type: "integer" as const, default: 15 },
        stock_meaning: { type: "string" as const, enum: ["available", "on_hand"], default: "available" },
        api_secret: { type: "string" as const, writeOnly: true, default: "x" },
        price_list: { type: "string" as const },
      },
    };
    expect(formDefaults(schema)).toEqual({ sync_minutes: 15, stock_meaning: "available" });
    expect(formDefaults(null)).toEqual({});
  });
});
