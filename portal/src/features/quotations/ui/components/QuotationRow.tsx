import { Link } from "react-router";

import { money } from "@/shared/lib/format";
import { StatusBadge } from "@/shared/ui/StatusBadge";

import type { QuotationSummary } from "../../model/types";

export function QuotationRow({ item }: { item: QuotationSummary }) {
  return (
    <li>
      <Link className="row" to={`/quotations/${item.quotation_id}`}>
        <span>
          <strong>{item.number}</strong>
          {item.current_version !== null && <span className="muted"> v{item.current_version}</span>}
          <br />
          <span className="muted">{item.customer_reference ?? "No customer reference"}</span>
        </span>
        <span className="row-end">
          <StatusBadge status={item.status} />
          <span className="amount">{money(item.total, item.currency)}</span>
        </span>
      </Link>
    </li>
  );
}
