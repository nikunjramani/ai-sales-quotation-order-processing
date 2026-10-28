import { useStockHistory } from "../../hooks/useCatalogue";
import { useStockForm } from "../../hooks/useCatalogueForms";
import type { Product } from "../../model/types";
import { ageText, stockLine } from "../../services/priceService";
import { dateTime } from "@/shared/lib/format";
import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

interface Props {
  product: Product;
  maxStockAgeSeconds: number | null;
  editable: boolean;
}

/** The latest count, its "as of" time, the history, and a form to record a count (Q21). */
export function StockPanel({ product, maxStockAgeSeconds, editable }: Props) {
  const history = useStockHistory(product.product_id);
  const form = useStockForm(product.product_id);
  const stock = product.stock;
  return (
    <section className="card">
      <h2>Stock</h2>
      {stock ? (
        <p>
          <strong>{stockLine(stock)}</strong>{" "}
          <span className="muted small">as of {dateTime(stock.as_of)}</span>{" "}
          {stock.stale && (
            <span className="badge warn">
              Older than {ageText(maxStockAgeSeconds)}: approvals will ask for a stock check
            </span>
          )}
        </p>
      ) : (
        <p className="muted">No count yet. Stock is optional and never blocks a quotation.</p>
      )}
      {editable && !product.archived_at && (
        <form onSubmit={form.submit}>
          <label htmlFor="stock-quantity">Quantity in {product.unit}</label>
          <input
            id="stock-quantity"
            inputMode="decimal"
            disabled={form.notTracked}
            value={form.quantity}
            onChange={(event) => form.setQuantity(event.target.value)}
          />
          <label>
            <input
              type="checkbox"
              checked={form.notTracked}
              onChange={(event) => form.setNotTracked(event.target.checked)}
            />{" "}
            Not tracked (unknown quantity)
          </label>
          <label htmlFor="stock-as-of">Counted at (leave empty for now)</label>
          <input
            id="stock-as-of"
            type="datetime-local"
            value={form.asOf ?? ""}
            onChange={(event) => form.setAsOf(event.target.value || null)}
          />
          <label htmlFor="stock-note">Note (optional)</label>
          <input id="stock-note" maxLength={500} value={form.note} onChange={(event) => form.setNote(event.target.value)} />
          <ErrorMessage message={form.problem ?? form.error} />
          <button
            type="submit"
            disabled={form.busy || (!form.quantity && !form.notTracked) || Boolean(form.problem)}
          >
            Record count
          </button>
        </form>
      )}
      <h3>History</h3>
      <QueryState isLoading={history.isLoading} error={history.error} isEmpty={history.data?.length === 0} emptyText="No counts yet.">
        <ul className="plain">
          {(history.data ?? []).map((count) => (
            <li key={count.stock_id}>
              {stockLine(count)} as of {dateTime(count.as_of)} · {count.recorded_by}
              {count.note && <span className="muted"> · {count.note}</span>}
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}
