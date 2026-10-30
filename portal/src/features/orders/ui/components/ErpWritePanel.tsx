import { type FormEvent, useState } from "react";

import { useCurrentTenant } from "@/features/tenant";
import { dateTime } from "@/shared/lib/format";
import { ErrorMessage } from "@/shared/ui/QueryState";

import { useOrderActions } from "../../hooks/useOrders";
import type { OrderDetail } from "../../model/types";
import { attentionOperation, operationText } from "../../services/orderService";

/**
 * The order's ERP write (intent before call). When it failed, or is still unknown after the
 * checking window, staff decide, each with a confirmation: "it is in the ERP" (type its
 * number) or "it is not in the ERP: send it again" (same reference, searched first).
 */
export function ErpWritePanel({ order }: { order: OrderDetail }) {
  const { can } = useCurrentTenant();
  const { resolve } = useOrderActions(order.order_id);
  const [number, setNumber] = useState("");
  const [confirming, setConfirming] = useState<"found" | "not_found" | null>(null);
  const latest = order.operations.at(-1);
  if (!latest) return null;
  const attention = attentionOperation(order.operations);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!attention || !confirming) return;
    resolve.mutate(
      {
        operationId: attention.operation_id,
        resolution: confirming,
        erpOrderId: confirming === "found" ? number.trim() : null,
      },
      { onSuccess: () => setConfirming(null) },
    );
  };
  const attempts = `${latest.attempts} attempt${latest.attempts === 1 ? "" : "s"}`;
  return (
    <section className="card">
      <h2>ERP</h2>
      <p>
        {operationText(latest)}{" "}
        <span className="muted small">
          (reference {latest.external_reference}, {attempts}, {dateTime(latest.updated_at)})
        </span>
      </p>
      {latest.last_error && <p className="muted small">Last answer: {latest.last_error}</p>}
      {attention && can("orders:manage") && (
        <form onSubmit={submit}>
          <p className="notice">
            Check the ERP for the reference <code>{attention.external_reference}</code>.
          </p>
          <div className="row-actions">
            <button type="button" className="secondary" onClick={() => setConfirming("found")}>
              It is in the ERP
            </button>
            <button type="button" className="secondary" onClick={() => setConfirming("not_found")}>
              It is not in the ERP: send it again
            </button>
          </div>
          {confirming === "found" && (
            <label>
              The order number in the ERP
              <input
                value={number}
                required
                maxLength={140}
                onChange={(event) => setNumber(event.target.value)}
              />
            </label>
          )}
          {confirming && (
            <button className="primary" type="submit" disabled={resolve.isPending}>
              {confirming === "found" ? "Confirm: record this ERP order" : "Confirm: send it again"}
            </button>
          )}
          <ErrorMessage message={resolve.error?.message} />
        </form>
      )}
    </section>
  );
}
