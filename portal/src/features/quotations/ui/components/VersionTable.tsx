import { dateTime, percent } from "@/shared/lib/format";
import { StatusBadge } from "@/shared/ui/StatusBadge";

import type { Version } from "../../model/types";

/** The exact content of one version: what the manager approves. */
export function VersionTable({ version }: { version: Version }) {
  const content = version.content;
  return (
    <section className="card">
      <h2>Quotation content</h2>
      {content.stock_review_required && (
        <p className="notice">At least one line is not confirmed as in stock.</p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th className="num">Qty</th>
              <th className="num">Unit price</th>
              <th className="num">Total</th>
              <th>Stock</th>
            </tr>
          </thead>
          <tbody>
            {content.lines.map((line) => (
              <tr key={line.line_index}>
                <td>
                  <strong>{line.sku}</strong>
                  <br />
                  <span className="muted">{line.description}</span>
                  <br />
                  <span className="muted small">
                    Price list {line.price_list_id} v{line.price_list_version}
                  </span>
                </td>
                <td className="num">
                  {line.quantity} {line.unit}
                </td>
                <td className="num">{line.unit_price}</td>
                <td className="num">{line.line_total}</td>
                <td>
                  <StatusBadge status={line.stock_status} />
                  <br />
                  <span className="muted small">{line.stock_note}</span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3}>Subtotal</td>
              <td className="num">{content.subtotal}</td>
              <td />
            </tr>
            <tr>
              <td colSpan={3}>Tax ({percent(content.policy.tax_rate)}%)</td>
              <td className="num">{content.tax}</td>
              <td />
            </tr>
            <tr className="total">
              <td colSpan={3}>Total ({content.currency})</td>
              <td className="num">{content.total}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="muted small">
        Calculated {dateTime(content.calculated_at)} · content hash{" "}
        <code>{version.content_sha256.slice(0, 12)}</code>
      </p>
    </section>
  );
}
