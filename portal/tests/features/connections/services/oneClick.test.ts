import { describe, expect, it } from "vitest";

import type { AvailableTool, Connection, PendingAction } from "@/features/connections/model/types";
import {
  disableConfirmed,
  enablable,
  formFields,
  needsCostTick,
  pollInterval,
  stepTexts,
} from "@/features/connections/services/connectionService";

const TOOL: AvailableTool = {
  provider_key: "future_tool",
  provider_name: "Future tool",
  kind: "one_click",
  purposes: ["customer_messages"],
  free: true,
  cost_note: "Free",
};

const CONNECTION: Connection = {
  connection_id: "c1",
  provider_key: "future_tool",
  provider_name: "Future tool",
  display_name: "Future tool",
  purposes: ["customer_messages"],
  status: "setting_up",
  last_error: null,
  created_at: "2026-10-29T10:00:00Z",
  chat: null,
};

const STEPS: PendingAction = {
  action_id: "link",
  kind: "show_steps",
  title: "Connect",
  steps: ["Send /link (press Enable again for a new one) to our bot"],
  url: null,
  form_schema: null,
  expires_at: null,
  once: {},
};

describe("one-click tools (phase 5)", () => {
  it("asks for the cost tick only when a tool may cost money", () => {
    expect(needsCostTick(TOOL)).toBe(false);
    expect(needsCostTick({ ...TOOL, free: false, cost_note: "About $1 a month" })).toBe(true);
  });

  it("offers a tool until the business has a connection of it that is not disabled", () => {
    expect(enablable([TOOL], [])).toEqual([TOOL]);
    expect(enablable([TOOL], [CONNECTION])).toEqual([]);
    expect(enablable([TOOL], [{ ...CONNECTION, status: "disabled" }])).toEqual([TOOL]);
    expect(enablable([{ ...TOOL, kind: "hosted_chat" }], [])).toEqual([]);
  });

  it("polls only while something is being set up", () => {
    expect(pollInterval([CONNECTION])).toBe(5000);
    expect(pollInterval([{ ...CONNECTION, status: "active" }])).toBe(false);
    expect(pollInterval(undefined)).toBe(false);
  });

  it("fills in the one-time code this browser still knows", () => {
    expect(stepTexts(STEPS, { code: "AB12CD34EF" })).toEqual(["Send /link AB12CD34EF to our bot"]);
    expect(stepTexts(STEPS, {})).toEqual(STEPS.steps);
  });

  it("builds form fields from the package's schema, secrets as password inputs", () => {
    const fields = formFields({
      required: ["legal_name"],
      properties: {
        legal_name: { type: "string", title: "Legal name" },
        employees: { type: "integer" },
        api_secret: { type: "string", writeOnly: true, format: "password" },
        country: { type: "string", enum: ["IN", "US"] },
        consent: { type: "boolean" },
      },
    });
    expect(fields.map((field) => [field.name, field.input, field.required])).toEqual([
      ["legal_name", "text", true],
      ["employees", "number", false],
      ["api_secret", "password", false],
      ["country", "select", false],
      ["consent", "checkbox", false],
    ]);
  });

  it("disables only after the exact name is typed", () => {
    expect(disableConfirmed(" Future tool ", CONNECTION)).toBe(true);
    expect(disableConfirmed("future tool", CONNECTION)).toBe(false);
  });
});
