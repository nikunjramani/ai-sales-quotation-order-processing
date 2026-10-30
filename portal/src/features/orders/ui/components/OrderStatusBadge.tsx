import type { OrderStatus } from "../../model/types";
import { STATUS_LABELS } from "../../services/orderService";

const TONES: Record<OrderStatus, string> = {
  placed: "info",
  confirmed: "good",
  in_progress: "info",
  shipped: "good",
  delivered: "good",
  cancelled: "bad",
  on_hold: "warn",
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return <span className={`badge ${TONES[status]}`}>{STATUS_LABELS[status]}</span>;
}
