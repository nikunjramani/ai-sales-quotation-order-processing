// Service: pure rules for showing documents and deliveries. No React, no HTTP.

import type { Delivery, DeliveryOverview, DeliveryStatus } from "../model/types";

interface StatusView {
  label: string;
  tone: "good" | "bad" | "warn" | "info";
  /** What a person should know or do; null when nothing is needed. */
  help: string | null;
}

export const DELIVERY_STATUS: Record<DeliveryStatus, StatusView> = {
  pending: { label: "Preparing", tone: "info", help: null },
  sending: { label: "Sending", tone: "info", help: null },
  available: {
    label: "Available to the customer",
    tone: "good",
    help: "The customer's system can download it with its API key.",
  },
  sent: { label: "Sent", tone: "good", help: null },
  failed: {
    label: "Failed",
    tone: "bad",
    help: "It was not delivered (cause above). Resending from the portal is not available yet.",
  },
  unknown: {
    label: "Outcome unknown",
    tone: "warn",
    help: "It may or may not have arrived; it is not resent automatically, to avoid duplicates.",
  },
};

const IN_PROGRESS: readonly DeliveryStatus[] = ["pending", "sending"];

/** True while the worker still has something to do, so the screen should keep refreshing. */
export function deliveryInProgress(overview: DeliveryOverview | undefined): boolean {
  if (!overview) return false;
  if (!overview.deliveries.length) return true; // approved, delivery not queued yet
  return overview.deliveries.some((delivery) => IN_PROGRESS.includes(delivery.status));
}

const CHANNELS: Record<string, string> = { api: "API client", email: "Email" };

export function channelLabel(channel: string): string {
  return CHANNELS[channel] ?? channel;
}

/** Short form of a hash for display; the full value is in the title attribute. */
export function shortHash(sha256: string): string {
  return sha256.slice(0, 12);
}

export function needsAttention(delivery: Delivery): boolean {
  return delivery.status === "failed" || delivery.status === "unknown";
}
