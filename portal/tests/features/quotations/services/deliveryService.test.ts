import { describe, expect, it } from "vitest";

import type { Delivery, DeliveryOverview } from "@/features/quotations/model/types";
import {
  DELIVERY_STATUS,
  channelLabel,
  deliveryInProgress,
  needsAttention,
  shortHash,
} from "@/features/quotations/services/deliveryService";

function delivery(status: Delivery["status"]): Delivery {
  return {
    delivery_id: `d-${status}`,
    version: 1,
    channel: "api",
    recipient: "api-key:1",
    status,
    provider_reference: null,
    last_error: null,
    created_at: "2026-10-23T10:00:00Z",
    updated_at: "2026-10-23T10:00:00Z",
    delivered_at: null,
    first_downloaded_at: null,
  };
}

function overview(...statuses: Delivery["status"][]): DeliveryOverview {
  return { document: null, deliveries: statuses.map(delivery) };
}

describe("deliveryInProgress", () => {
  it("keeps refreshing until every delivery has a final outcome", () => {
    expect(deliveryInProgress(undefined)).toBe(false);
    expect(deliveryInProgress(overview())).toBe(true); // approved, not queued yet
    expect(deliveryInProgress(overview("pending"))).toBe(true);
    expect(deliveryInProgress(overview("available", "sending"))).toBe(true);
    expect(deliveryInProgress(overview("available"))).toBe(false);
    expect(deliveryInProgress(overview("failed", "unknown", "sent"))).toBe(false);
  });
});

describe("status views", () => {
  it("flags only failed and unknown deliveries for a person", () => {
    expect(needsAttention(delivery("failed"))).toBe(true);
    expect(needsAttention(delivery("unknown"))).toBe(true);
    expect(needsAttention(delivery("available"))).toBe(false);
    expect(DELIVERY_STATUS.unknown.help).toContain("not resent automatically");
    expect(DELIVERY_STATUS.available.tone).toBe("good");
  });

  it("names channels and shortens hashes for display", () => {
    expect(channelLabel("api")).toBe("API client");
    expect(channelLabel("telegram")).toBe("telegram");
    expect(shortHash("abcdef0123456789".repeat(4))).toBe("abcdef012345");
  });
});
