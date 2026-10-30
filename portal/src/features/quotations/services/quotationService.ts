// Service: pure quotation rules for the UI. No React, no HTTP, so it is easy to test.

import type {
  ApprovalAction,
  EditableLine,
  PricingIssue,
  QuotationDetail,
  QuotationStatus,
  Version,
} from "../model/types";

export const QUOTATION_FILTERS = [
  { id: "waiting", label: "Waiting for approval", statuses: ["pending_approval"] },
  { id: "revision", label: "Needs changes", statuses: ["revision_requested", "pricing_failed"] },
  { id: "approved", label: "Approved", statuses: ["approved"] },
  { id: "accepted", label: "Accepted", statuses: ["accepted"] },
  {
    id: "closed",
    label: "Declined / expired / withdrawn",
    statuses: ["declined", "expired", "withdrawn"],
  },
  { id: "all", label: "All", statuses: [] },
] as const satisfies readonly { id: string; label: string; statuses: readonly QuotationStatus[] }[];

export type QuotationFilterId = (typeof QUOTATION_FILTERS)[number]["id"];

export function filterById(id: string | null): (typeof QUOTATION_FILTERS)[number] {
  return QUOTATION_FILTERS.find((filter) => filter.id === id) ?? QUOTATION_FILTERS[0];
}

export const DECISION_ACTIONS: readonly { action: ApprovalAction; label: string; tone: string }[] = [
  { action: "approve", label: "Approve", tone: "primary" },
  { action: "request_revision", label: "Ask for changes", tone: "secondary" },
  { action: "reject", label: "Reject", tone: "danger" },
];

/** Mirrors the server rule so the person gets instant feedback; the server still decides. */
export function decisionProblem(action: ApprovalAction, reason: string): string | null {
  if (action !== "approve" && !reason.trim()) {
    return "Please give a reason for rejecting or requesting a revision.";
  }
  if (reason.length > 1000) return "The reason can be at most 1000 characters.";
  return null;
}

export function currentVersion(detail: QuotationDetail): Version | null {
  return detail.versions.at(-1) ?? null;
}

const EMPTY_LINE: EditableLine = { sku: "", quantity: "1", unit: "each" };

/** Starting lines for a revision: the current version's lines, or one empty line. */
export function initialRevisionLines(detail: QuotationDetail): EditableLine[] {
  const lines = currentVersion(detail)?.content.lines ?? [];
  return lines.length ? lines.map(({ sku, quantity, unit }) => ({ sku, quantity, unit })) : [EMPTY_LINE];
}

export function emptyLine(): EditableLine {
  return { ...EMPTY_LINE };
}

/** Lines to send: blank SKUs dropped, text trimmed. Quantities stay strings (exact decimals). */
export function cleanLines(lines: readonly EditableLine[]): EditableLine[] {
  return lines
    .map((line) => ({ sku: line.sku.trim(), quantity: line.quantity.trim(), unit: line.unit.trim() }))
    .filter((line) => line.sku);
}

export function revisionProblem(lines: readonly EditableLine[], reason: string): string | null {
  if (!cleanLines(lines).length) return "Add at least one product line.";
  if (!reason.trim()) return "Describe what changed and why.";
  return null;
}

/** Pricing issues the server returns with a 422 when lines cannot be priced. */
export function pricingIssuesFrom(detail: unknown): PricingIssue[] {
  if (detail && typeof detail === "object" && "issues" in detail) {
    const issues = (detail as { issues: unknown }).issues;
    if (Array.isArray(issues)) return issues as PricingIssue[];
  }
  return [];
}
