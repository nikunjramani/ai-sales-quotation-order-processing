import { usePriceHistory } from "../../hooks/useCatalogue";
import { usePriceForm } from "../../hooks/useCatalogueForms";
import type { Product } from "../../model/types";
import { evidenceLabel, PRICE_STATE_LABEL, priceLine, tomorrow } from "../../services/priceService";
import { dateTime } from "@/shared/lib/format";
import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

interface Props {
  product: Product;
  currency: string | null;
  timeZone: string | null;
  editable: boolean;
}

/** Current and scheduled price, the full history, and a form to add a price. */
export function PricePanel({ product, currency, timeZone, editable }: Props) {
  const history = usePriceHistory(product.product_id);
  const form = usePriceForm(product.product_id, timeZone);
  const current = product.current_price;
  return (
    <section className="card">
      <h2>Price</h2>
      {current ? (
        <p>
          <strong>{priceLine(current)}</strong>, excluding tax
          <br />
          <span className="muted small">
            Since {dateTime(current.effective_from)} · {evidenceLabel(current)}
          </span>
        </p>
      ) : (
        <p className="badge warn">No price: this product cannot be quoted yet.</p>
      )}
      {product.scheduled_price && (
        <p className="notice">
          From {dateTime(product.scheduled_price.effective_from)}:{" "}
          {priceLine(product.scheduled_price)}
        </p>
      )}
      {editable && !product.archived_at && (
        <form onSubmit={form.submit}>
          {currency === null ? (
            <p className="card warn">Set the business currency in Settings, Pricing first.</p>
          ) : (
            <>
              <label htmlFor="price-amount">New price per {product.unit} in {currency}, excluding tax</label>
              <input
                id="price-amount"
                inputMode="decimal"
                value={form.amount}
                onChange={(event) => form.setAmount(event.target.value)}
              />
              <fieldset>
                <legend>Starts</legend>
                <label>
                  <input type="radio" checked={form.startDate === null} onChange={() => form.setStartDate(null)} />{" "}
                  Now
                </label>
                <label>
                  <input
                    type="radio"
                    checked={form.startDate !== null}
                    onChange={() => form.setStartDate(tomorrow())}
                  />{" "}
                  On a later date (midnight{timeZone ? `, ${timeZone}` : ""})
                </label>
                {form.startDate !== null && (
                  <input
                    aria-label="Start date"
                    type="date"
                    min={tomorrow()}
                    value={form.startDate}
                    onChange={(event) => form.setStartDate(event.target.value)}
                  />
                )}
              </fieldset>
              <label htmlFor="price-note">Note (optional)</label>
              <input id="price-note" maxLength={500} value={form.note} onChange={(event) => form.setNote(event.target.value)} />
              <ErrorMessage message={form.problem ?? form.error} />
              <p className="muted small">
                Prices are never overwritten: a new price is added to the history. Open
                quotations keep their price; a customer accepting after a change gets a
                revised quotation for approval.
              </p>
              <button type="submit" disabled={form.busy || !form.amount || Boolean(form.problem)}>
                Add price
              </button>
            </>
          )}
        </form>
      )}
      <h3>History</h3>
      <QueryState isLoading={history.isLoading} error={history.error} isEmpty={history.data?.length === 0} emptyText="No prices yet.">
        <ul className="plain">
          {(history.data ?? []).map((price) => (
            <li key={price.price_id}>
              {price.state && <span className="badge">{PRICE_STATE_LABEL[price.state]}</span>}{" "}
              {priceLine(price)} from {dateTime(price.effective_from)} · revision {price.revision} ·{" "}
              {price.created_by}
              {price.note && <span className="muted"> · {price.note}</span>}
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}
