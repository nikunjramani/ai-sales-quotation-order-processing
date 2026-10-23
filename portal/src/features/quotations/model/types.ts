// Shapes returned by the quotation API. Money stays a string: the portal shows the exact amounts
// the server calculated and never does arithmetic on them.

export type QuotationStatus =
  | "pricing_failed"
  | "pending_approval"
  | "revision_requested"
  | "revision_submitted"
  | "approved"
  | "rejected";

export type ApprovalAction = "approve" | "reject" | "request_revision";

export interface QuotationSummary {
  quotation_id: string;
  enquiry_id: string;
  number: string;
  status: QuotationStatus;
  current_version: number | null;
  customer_reference: string | null;
  currency: string | null;
  total: string | null;
  updated_at: string;
}

export interface QuotationLine {
  line_index: number;
  sku: string;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  line_total: string;
  price_list_id: string;
  price_list_version: string;
  stock_status: string;
  stock_available: string | null;
  stock_note: string;
}

export interface VersionContent {
  currency: string;
  lines: QuotationLine[];
  subtotal: string;
  tax: string;
  total: string;
  stock_review_required: boolean;
  calculated_at: string;
  policy: { tax_rate: string; rounding: string; minor_units: number; version: number };
}

export interface Version {
  version: number;
  content: VersionContent;
  content_sha256: string;
  created_by: string;
  reason: string | null;
  created_at: string;
}

export interface Task {
  task_id: string;
  version: number;
  content_sha256: string;
  status: "pending" | "approved" | "rejected" | "revision_requested";
  created_at: string;
  decided_at: string | null;
}

export interface Decision {
  decision_id: string;
  task_id: string;
  version: number;
  action: ApprovalAction;
  actor_subject: string;
  reason: string | null;
  transport: string;
  decided_at: string;
}

export interface PricingIssue {
  line_index: number;
  sku: string;
  code: string;
  message: string;
}

export interface QuotationDetail {
  summary: QuotationSummary;
  enquiry_text: string;
  pricing_issues: PricingIssue[];
  versions: Version[];
  tasks: Task[];
  decisions: Decision[];
  pending_task: Task | null;
  can_decide: boolean;
  can_revise: boolean;
}

export interface EditableLine {
  sku: string;
  quantity: string;
  unit: string;
}

export interface DecisionRequest {
  command_id: string;
  action: ApprovalAction;
  content_sha256: string;
  reason: string | null;
}

export interface RevisionRequest {
  command_id: string;
  base_version: number | null;
  lines: EditableLine[];
  reason: string;
}

// Approved PDF and its delivery to the customer (M5).
export type DeliveryStatus = "pending" | "sending" | "available" | "sent" | "failed" | "unknown";

export interface QuotationDocument {
  version: number;
  sha256: string;
  size_bytes: number;
  renderer: string;
  created_at: string;
}

export interface Delivery {
  delivery_id: string;
  version: number;
  channel: string;
  recipient: string;
  status: DeliveryStatus;
  provider_reference: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  delivered_at: string | null;
  first_downloaded_at: string | null;
}

export interface DeliveryOverview {
  document: QuotationDocument | null;
  deliveries: Delivery[];
}

export interface RevisionResult {
  quotation_id: string;
  version: number;
  replayed: boolean;
}
