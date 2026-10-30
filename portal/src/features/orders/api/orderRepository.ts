import { http, tenantPath } from "@/shared/api/httpClient";

import type {
  Order,
  OrderDetail,
  OrderListFilter,
  OrderSettings,
  OrderStatus,
} from "../model/types";

const id = encodeURIComponent;

export const orderRepository = {
  list: (tenantId: string, filter: OrderListFilter) =>
    http<Order[]>(tenantPath(tenantId, "/orders"), {
      query: {
        status: filter.status,
        needs_attention: filter.needsAttention ? "true" : undefined,
      },
    }),

  detail: (tenantId: string, orderId: string) =>
    http<OrderDetail>(tenantPath(tenantId, `/orders/${id(orderId)}`)),

  /** 404 means the quotation has no order yet. */
  forQuotation: (tenantId: string, quotationId: string) =>
    http<Order>(tenantPath(tenantId, `/quotations/${id(quotationId)}/order`)),

  create: (tenantId: string, quotationId: string, erpCustomer: string | null) =>
    http<Order>(tenantPath(tenantId, `/quotations/${id(quotationId)}/order`), {
      method: "POST",
      body: { erp_customer: erpCustomer },
    }),

  move: (tenantId: string, orderId: string, status: OrderStatus, reason: string | null) =>
    http<Order>(tenantPath(tenantId, `/orders/${id(orderId)}/status`), {
      method: "POST",
      body: { status, reason },
    }),

  resolve: (
    tenantId: string,
    orderId: string,
    operationId: string,
    resolution: "found" | "not_found",
    erpOrderId: string | null,
  ) =>
    http<Order>(
      tenantPath(tenantId, `/orders/${id(orderId)}/operations/${id(operationId)}/resolve`),
      { method: "POST", body: { resolution, erp_order_id: erpOrderId } },
    ),

  settings: (tenantId: string) => http<OrderSettings>(tenantPath(tenantId, "/order-settings")),

  setSettings: (tenantId: string, value: OrderSettings) =>
    http<OrderSettings>(tenantPath(tenantId, "/order-settings"), { method: "PUT", body: value }),
};
