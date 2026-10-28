import { describe, expect, it } from "vitest";

import type { ThreadMessage } from "@/features/conversations/model/types";
import {
  authorLabel,
  consentLabel,
  deliveryLabel,
  preview,
} from "@/features/conversations/services/conversationService";
import { originsFromText } from "@/features/connections/services/connectionService";

const ours: ThreadMessage = {
  seq: 2,
  direction: "outbound",
  author: "system",
  text: "We need a bit more information:",
  at: "2026-10-28T10:00:00Z",
  enquiry_id: "e1",
  template_key: "clarification_questions",
  outbound_status: "failed",
  outbound_error: "The customer opted out of messages",
};

describe("conversation display rules", () => {
  it("names who wrote and says honestly whether our message went out", () => {
    expect(authorLabel(ours)).toBe("Sent automatically");
    expect(deliveryLabel(ours)).toBe("Not sent: The customer opted out of messages");
    expect(authorLabel({ ...ours, direction: "inbound", author: "customer" })).toBe("Customer");
    expect(deliveryLabel({ ...ours, direction: "inbound" })).toBeNull();
  });

  it("shows consent and short previews", () => {
    expect(consentLabel("opted_out")).toBe("Opted out (STOP)");
    expect(preview("first line\nsecond")).toBe("first line");
    expect(preview("x".repeat(200), 10)).toHaveLength(10);
  });

  it("reads one website per line or space", () => {
    expect(originsFromText(" https://a.example\n\nhttps://b.example ")).toEqual([
      "https://a.example",
      "https://b.example",
    ]);
  });
});
