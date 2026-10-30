import { useState } from "react";
import { Link } from "react-router";

import { useCurrentTenant } from "@/features/tenant";
import { dateTime, money } from "@/shared/lib/format";
import { FilterTabs } from "@/shared/ui/FilterTabs";
import { QueryState } from "@/shared/ui/QueryState";

import { useOrderSettings, useOrders } from "../../hooks/useOrders";
import type { OrderListFilter, OrderStatus } from "../../model/types";
import { OrderStatusBadge } from "../components/OrderStatusBadge";

const TABS = [
  { id: "all", label: "All" },
  { id: "attention", label: "Needs attention" },
  { id: "on_hold", label: "On hold" },
  { id: "placed", label: "Placed" },
  { id: "confirmed", label: "Confirmed" },
  { id: "shipped", label: "Shipped" },
  { id: "delivered", label: "Delivered" },
] as const;

function filterFor(tab: string): OrderListFilter {
  if (tab === "all") return {};
  if (tab === "attention") return { needsAttention: true };
  return { status: tab as OrderStatus };
}

/** Every order, newest first (refreshes every 15 seconds while ERP writes finish). */
export function OrderListPage() {
  const [tab, setTab] = useState("all");
  const orders = useOrders(filterFor(tab));
  const { can } = useCurrentTenant();
  return (
    <section>
      <h1>Orders</h1>
      {can("tenant:manage") && <CreationSetting />}
      <FilterTabs tabs={TABS} selected={tab} onSelect={setTab} />
      <QueryState isLoading={orders.isLoading} error={orders.error} isEmpty={orders.data?.length === 0}>
        <ul className="list">
          {orders.data?.map((order) => (
            <li key={order.order_id}>
              <Link className="row" to={`/orders/${order.order_id}`}>
                <span>
                  <strong>{order.order_number}</strong>{" "}
                  <span className="muted small">from {order.quotation_number}</span>
                  <br />
                  {money(order.total, order.currency)} ·{" "}
                  {order.fulfilment === "erp" ? "ERP" : "kept here"}
                  {order.operation_status === "failed" || order.operation_status === "needs_attention" ? (
                    <strong> · needs attention</strong>
                  ) : null}
                  <br />
                  <span className="muted small">{dateTime(order.created_at)}</span>
                </span>
                <OrderStatusBadge status={order.status} />
              </Link>
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}

/** Q1: orders are created by staff (default) or automatically on acceptance. */
function CreationSetting() {
  const { query, save } = useOrderSettings();
  if (!query.data) return null;
  return (
    <label className="small">
      <input
        type="checkbox"
        checked={query.data.order_creation === "automatic"}
        disabled={save.isPending}
        onChange={(event) => save.mutate(event.target.checked ? "automatic" : "staff")}
      />{" "}
      Create the order automatically when a customer accepts a quotation (otherwise staff press
      "Create order")
    </label>
  );
}
