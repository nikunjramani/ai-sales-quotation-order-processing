import { CircleCheck, CircleX, Clock, TriangleAlert, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

// Plain words for every status (user decision 2026-10-30, ADR 0025). Codes stay the same.
const LABELS: Record<string, string> = {
  pricing_failed: "Price missing",
  pending_approval: "Waiting for approval",
  revision_requested: "Needs changes",
  revision_submitted: "Changes sent",
  approved: "Approved",
  rejected: "Rejected",
  accepted: "Accepted",
  declined: "Declined",
  expired: "Expired",
  withdrawn: "Withdrawn",
  pending: "Pending",
  needs_review: "Needs a person",
  needs_clarification: "Ask the customer",
  ready_for_quotation: "Ready to quote",
  ready_for_extraction: "Reading…",
  received: "Received",
  available: "In stock",
};

const TONES: Record<string, string> = {
  approved: "good",
  accepted: "good",
  available: "good",
  declined: "bad",
  rejected: "bad",
  pricing_failed: "bad",
  needs_review: "warn",
  needs_clarification: "warn",
  revision_requested: "warn",
  pending_approval: "info",
  pending: "info",
};

/** Each colour also has its own shape, so the status is clear without seeing colour. */
export const TONE_ICONS: Record<string, LucideIcon> = {
  good: CircleCheck,
  bad: CircleX,
  warn: TriangleAlert,
  info: Clock,
};

export function statusLabel(status: string): string {
  return LABELS[status] ?? status;
}

export function StatusBadge({ status }: { status: string }) {
  const tone = TONES[status] ?? "warn";
  return <ToneBadge tone={tone}>{statusLabel(status)}</ToneBadge>;
}

/** A badge for any tone; used by features that have their own status words. */
export function ToneBadge({ tone, children }: { tone: string; children: ReactNode }) {
  const Icon = TONE_ICONS[tone];
  return (
    <span className={`badge ${tone}`}>
      {Icon && <Icon size={14} aria-hidden="true" />}
      {children}
    </span>
  );
}
