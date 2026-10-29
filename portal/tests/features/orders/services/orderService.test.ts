import { describe, expect, it } from "vitest";

import type { Order, OrderOperation } from "@/features/orders/model/types";
import {
  attentionOperation,
  moveLabel,
  needsReason,
  nextStatuses,
  operationText,
} from "@/features/orders/services/orderService";

const ORDER: Order = {
  order_id: "o1",
  order_number: "O-1A2B3C4D",
  quotation_id: "q1",
  quotation_number: "Q-9F8E7D6C",
  version: 1,
  status: "placed",
  hold_reason: null,
  fulfilment: "local",
  erp_customer: null,
  erp_order_id: null,
  currency: "INR",
  subtotal: "8500.00",
  tax: "1530.00",
  total: "10030.00",
  lines: [],
  created_by: "sales@example.com",
  created_at: "2026-10-29T10:00:00Z",
  updated_at: "2026-10-29T10:00:00Z",
  operation_status: null,
};

const OPERATION: OrderOperation = {
  operation_id: "op1",
  external_reference: "QO-1",
  status: "succeeded",
  erp_order_id: "SAL-ORD-00001",
  attempts: 1,
  last_error: null,
  unknown_since: null,
  updated_at: "2026-10-29T10:00:00Z",
};

describe("orderService", () => {
  it("offers a local order the server's next steps and nothing after delivery", () => {
    expect(nextStatuses(ORDER)).toEqual(["confirmed", "on_hold", "cancelled"]);
    expect(nextStatuses({ ...ORDER, status: "shipped" })).toEqual(["delivered"]);
    expect(nextStatuses({ ...ORDER, status: "delivered" })).toEqual([]);
  });

  it("lets staff move an ERP order only while it is held before sending", () => {
    const erp = { ...ORDER, fulfilment: "erp" as const };
    expect(nextStatuses(erp)).toEqual([]);
    expect(nextStatuses({ ...erp, status: "on_hold" })).toEqual(["placed", "cancelled"]);
    expect(nextStatuses({ ...erp, status: "on_hold", erp_order_id: "SO-1" })).toEqual([]);
    expect(moveLabel({ ...erp, status: "on_hold" }, "placed")).toBe("Release and send to the ERP");
  });

  it("asks for a reason to cancel or hold", () => {
    expect(needsReason("cancelled")).toBe(true);
    expect(needsReason("on_hold")).toBe(true);
    expect(needsReason("confirmed")).toBe(false);
  });

  it("finds the ERP write that needs staff and says what is known", () => {
    expect(attentionOperation([OPERATION])).toBeNull();
    const stuck = { ...OPERATION, status: "needs_attention" as const };
    expect(attentionOperation([OPERATION, stuck])).toBe(stuck);
    expect(operationText(OPERATION)).toBe("In the ERP as SAL-ORD-00001");
    expect(operationText({ ...OPERATION, status: "unknown" })).toMatch(/keep checking/);
  });
});
