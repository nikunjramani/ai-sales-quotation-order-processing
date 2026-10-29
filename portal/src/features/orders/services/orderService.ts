import type { Order, OrderOperation, OrderStatus } from "../model/types";

export const STATUS_LABELS: Record<OrderStatus, string> = {
  placed: "Placed",
  confirmed: "Confirmed",
  in_progress: "In progress",
  shipped: "Shipped",
  delivered: "Delivered",
  cancelled: "Cancelled",
  on_hold: "On hold",
};

// The same moves the server allows for a local order (domain/orders.py LOCAL_TRANSITIONS).
const LOCAL_MOVES: Record<OrderStatus, OrderStatus[]> = {
  placed: ["confirmed", "on_hold", "cancelled"],
  confirmed: ["in_progress", "shipped", "on_hold", "cancelled"],
  in_progress: ["shipped", "on_hold", "cancelled"],
  shipped: ["delivered"],
  on_hold: ["placed", "confirmed", "in_progress", "cancelled"],
  delivered: [],
  cancelled: [],
};

/** The next statuses staff may choose; an ERP order only while it is held before sending. */
export function nextStatuses(order: Order): OrderStatus[] {
  if (order.fulfilment === "erp") {
    return order.status === "on_hold" && order.erp_order_id === null ? ["placed", "cancelled"] : [];
  }
  return LOCAL_MOVES[order.status];
}

/** Cancelling and holding need a reason (the server checks it too). */
export function needsReason(target: OrderStatus): boolean {
  return target === "cancelled" || target === "on_hold";
}

export function moveLabel(order: Order, target: OrderStatus): string {
  if (order.fulfilment === "erp" && target === "placed") return "Release and send to the ERP";
  if (order.status === "on_hold" && target !== "cancelled") return `Release as ${STATUS_LABELS[target]}`;
  return `Mark ${STATUS_LABELS[target].toLowerCase()}`;
}

/** The ERP write staff must look at: failed (refused) or needs attention (still unknown). */
export function attentionOperation(operations: OrderOperation[]): OrderOperation | null {
  return operations.find((item) => item.status === "failed" || item.status === "needs_attention") ?? null;
}

export function operationText(operation: OrderOperation): string {
  switch (operation.status) {
    case "pending":
      return "Waiting to be written to the ERP";
    case "sending":
      return "Being written to the ERP";
    case "succeeded":
      return `In the ERP as ${operation.erp_order_id ?? "?"}`;
    case "failed":
      return "The ERP refused it";
    case "unknown":
      return "Not sure the ERP has it yet: we keep checking";
    case "needs_attention":
      return "Still not found in the ERP: please check it there";
  }
}

const EVENT_LABELS: Record<string, string> = {
  created: "Order created",
  status_changed: "Status changed",
  held: "Held: stock is short",
  erp_write_succeeded: "Written to the ERP",
  erp_write_failed: "The ERP refused it",
  erp_write_unknown: "ERP answer unknown",
  reconciled: "Found in the ERP",
  needs_attention: "Needs attention",
  resolved: "Resolved by staff",
  retried: "Sent again",
  ignored: "ERP status ignored",
};

export function eventLabel(type: string): string {
  return EVENT_LABELS[type] ?? type;
}
