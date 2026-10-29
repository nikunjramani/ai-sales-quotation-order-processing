// Service: pure display rules for conversations.

import type { ThreadMessage } from "../model/types";

/** Who wrote a message, in words staff understand. */
export function authorLabel(message: ThreadMessage): string {
  // Phase 5: what the business typed itself on its own tool account (e.g. Telegram).
  if (message.direction === "inbound") {
    return message.author === "staff" ? "Staff, on the tool" : "Customer";
  }
  return message.author === "staff" ? "Staff" : "Sent automatically";
}

/** Our messages show whether they actually went out (honest outbox statuses). */
export function deliveryLabel(message: ThreadMessage): string | null {
  if (message.direction === "inbound" || message.outbound_status === null) return null;
  const labels: Record<string, string> = {
    pending: "Waiting to send",
    sending: "Sending",
    available: "Available to the customer's system",
    sent: "Sent",
    delivered: "Delivered",
    failed: "Not sent",
    unknown: "Unknown; check with the tool",
  };
  const label = labels[message.outbound_status] ?? message.outbound_status;
  return message.outbound_error ? `${label}: ${message.outbound_error}` : label;
}

export function consentLabel(consent: string): string {
  return consent === "opted_out" ? "Opted out (STOP)" : "May receive messages";
}

/** First line of a message, for lists. */
export function preview(text: string, length = 120): string {
  const line = text.split("\n")[0] ?? "";
  return line.length > length ? `${line.slice(0, length - 1)}…` : line;
}
