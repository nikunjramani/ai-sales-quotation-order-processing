// Orders (phase 7, ADR 0024): what an accepted quotation becomes. Decimals are strings.

export type OrderStatus =
  | "placed"
  | "confirmed"
  | "in_progress"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "on_hold";

export type OperationStatus =
  | "pending"
  | "sending"
  | "succeeded"
  | "failed"
  | "unknown"
  | "needs_attention";

export interface OrderLine {
  line_index: number;
  sku: string;
  description: string;
  quantity: string;
  unit: string;
  unit_price: string;
  line_total: string;
}

export interface Order {
  order_id: string;
  order_number: string;
  quotation_id: string;
  quotation_number: string;
  version: number;
  status: OrderStatus;
  hold_reason: string | null;
  /** local: staff move the status here; erp: written to the ERP, whose status it follows. */
  fulfilment: "local" | "erp";
  erp_customer: string | null;
  erp_order_id: string | null;
  currency: string;
  subtotal: string;
  tax: string;
  total: string;
  lines: OrderLine[];
  created_by: string;
  created_at: string;
  updated_at: string;
  operation_status: OperationStatus | null;
}

export interface OrderEvent {
  event_id: string;
  type: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus | null;
  source: "system" | "staff" | "erp";
  actor: string;
  detail: Record<string, unknown>;
  occurred_at: string;
}

export interface OrderOperation {
  operation_id: string;
  external_reference: string;
  status: OperationStatus;
  erp_order_id: string | null;
  attempts: number;
  last_error: string | null;
  unknown_since: string | null;
  updated_at: string;
}

export interface OrderDetail extends Order {
  events: OrderEvent[];
  operations: OrderOperation[];
}

export type OrderCreation = "staff" | "automatic";

export interface OrderSettings {
  order_creation: OrderCreation;
}

export interface OrderListFilter {
  status?: OrderStatus;
  needsAttention?: boolean;
}
