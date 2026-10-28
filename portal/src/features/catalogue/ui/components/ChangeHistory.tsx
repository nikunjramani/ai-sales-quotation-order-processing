import { useChanges } from "../../hooks/useCatalogue";
import { dateTime } from "@/shared/lib/format";
import { QueryState } from "@/shared/ui/QueryState";

const FIELD_LABEL: Record<string, string> = {
  sku: "SKU",
  name: "name",
  unit: "unit",
  description: "notes",
  category_id: "category",
  minimum_quantity: "minimum quantity",
  quantity_step: "step",
};

/** Who changed what and when (the audit trail of product edits). */
export function ChangeHistory({ productId }: { productId: string }) {
  const changes = useChanges(productId);
  return (
    <section className="card">
      <h2>Changes</h2>
      <QueryState isLoading={changes.isLoading} error={changes.error} isEmpty={changes.data?.length === 0}>
        <ul className="plain">
          {(changes.data ?? []).map((change) => (
            <li key={`${change.created_at}-${change.action}`}>
              {dateTime(change.created_at)} · {change.actor} · {change.action}
              {change.action === "updated" && (
                <span className="muted">
                  {" "}
                  ({Object.keys(change.changes).map((field) => FIELD_LABEL[field] ?? field).join(", ")})
                </span>
              )}
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}
