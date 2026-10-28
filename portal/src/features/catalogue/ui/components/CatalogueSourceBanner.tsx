import type { CatalogueSummary } from "../../model/types";

/** Says where the products come from; read-only when they are not edited here (Q18). */
export function CatalogueSourceBanner({ summary }: { summary: CatalogueSummary }) {
  if (summary.source === null) {
    return (
      <p className="card warn">
        No product source is connected, so enquiries cannot be quoted yet.
      </p>
    );
  }
  if (!summary.source.editable) {
    return (
      <p className="notice">
        Products come from {summary.source.display_name}. Change them there; this list is
        read-only.
      </p>
    );
  }
  return null;
}
