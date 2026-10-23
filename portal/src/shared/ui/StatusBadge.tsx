const LABELS: Record<string, string> = {
  pricing_failed: "Cannot price",
  pending_approval: "Waiting for approval",
  revision_requested: "Revision requested",
  revision_submitted: "Revision submitted",
  approved: "Approved",
  rejected: "Rejected",
  pending: "Pending",
  needs_review: "Needs review",
  needs_clarification: "Needs clarification",
  ready_for_quotation: "Ready for quotation",
  ready_for_extraction: "Being read",
  received: "Received",
  available: "In stock",
};

const TONES: Record<string, string> = {
  approved: "good",
  available: "good",
  rejected: "bad",
  pricing_failed: "bad",
  needs_review: "warn",
  needs_clarification: "warn",
  revision_requested: "warn",
  pending_approval: "info",
  pending: "info",
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${TONES[status] ?? "warn"}`}>{LABELS[status] ?? status}</span>;
}
