// Service: pure rules for showing connections. No React, no HTTP. The screens decide by
// purposes and status, never by provider name, so a new tool needs no portal change.

import type { Connection, ConnectionStatus, Purpose } from "../model/types";

export const PURPOSE_LABEL: Record<Purpose, string> = {
  customer_messages: "Customer messages",
  manager_approvals: "Manager approvals",
  catalogue: "Product data",
  payments: "Payments",
  orders: "Orders",
};

export const STATUS_VIEW: Record<
  ConnectionStatus,
  { label: string; tone: "good" | "bad" | "warn" | "info" }
> = {
  setting_up: { label: "Setting up", tone: "info" },
  active: { label: "Active", tone: "good" },
  error: { label: "Needs attention", tone: "bad" },
  disabled: { label: "Disabled", tone: "warn" },
};

/** A manager can link their own account only on an active connection used for approvals. */
export function canLink(connection: Connection): boolean {
  return (
    connection.status === "active" &&
    connection.purposes.includes("manager_approvals")
  );
}

export function purposeText(connection: Connection): string {
  return connection.purposes
    .map((purpose) => PURPOSE_LABEL[purpose] ?? purpose)
    .join(", ");
}

/** "https://a.example\n\n https://b.example " -> ["https://a.example", "https://b.example"]. */
export function originsFromText(text: string): string[] {
  return text
    .split(/\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}
