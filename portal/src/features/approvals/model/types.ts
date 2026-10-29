export type LinkState = "open" | "decided" | "changed" | "expired";

export type ApprovalAction = "approve" | "reject" | "request_revision";

export interface ReviewLine {
  sku: string;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  line_total: string;
  stock_status: string;
}

/** What the signed approval link shows (phase 5): one request, exactly as it was sent. */
export interface ApprovalLink {
  tenant_id: string;
  business_name: string;
  quotation_id: string;
  number: string;
  version: number;
  state: LinkState;
  decided: ApprovalAction | null;
  expires_at: string;
  /** While open: decide on exactly this version. */
  content_sha256: string | null;
  customer_reference: string | null;
  content: {
    lines?: ReviewLine[];
    subtotal?: string;
    tax?: string;
    total?: string;
    currency?: string;
  } | null;
}

export interface LinkDecision {
  action: ApprovalAction;
  replayed: boolean;
}
