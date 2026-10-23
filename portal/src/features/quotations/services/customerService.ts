// Service: pure rules for showing the customer's side of a quotation (M6). No React, no HTTP.

import type { CustomerStatus, ResponseOutcome } from "../model/types";

interface View {
  label: string;
  tone: "good" | "bad" | "warn" | "info";
}

export const CUSTOMER_STATUS: Record<CustomerStatus, View> = {
  open: { label: "Waiting for the customer", tone: "info" },
  accepted: { label: "Accepted by the customer", tone: "good" },
  declined: { label: "Declined by the customer", tone: "bad" },
  expired: { label: "Expired", tone: "warn" },
  withdrawn: { label: "Withdrawn", tone: "warn" },
  being_revised: { label: "Being revised (prices changed)", tone: "info" },
  closed: { label: "Closed", tone: "bad" },
};

export const OUTCOME_LABEL: Record<ResponseOutcome, string> = {
  accepted: "Accepted",
  declined: "Declined",
  refused_changed: "Acceptance refused: prices changed, a revised version was drafted",
  withdrawn: "Withdrawn",
  expired: "Expired without an answer",
};

/** Mirrors the server rule for instant feedback; the server still decides. */
export function withdrawalProblem(reason: string): string | null {
  if (!reason.trim()) return "Please give a reason for withdrawing the quotation.";
  if (reason.length > 1000) return "The reason can be at most 1000 characters.";
  return null;
}
