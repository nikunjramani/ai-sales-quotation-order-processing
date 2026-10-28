import { useNavigate } from "react-router";

import { useProductActions } from "../../hooks/useCatalogue";
import type { Product } from "../../model/types";
import { ErrorMessage } from "@/shared/ui/QueryState";

/** Archive ("no longer sold", Q11), restore, or delete a product that was never used (Q12). */
export function ArchiveControls({ product }: { product: Product }) {
  const actions = useProductActions(product.product_id);
  const navigate = useNavigate();
  return (
    <section className="card">
      <h2>Availability</h2>
      {product.archived_at ? (
        <>
          <p>Archived: customers cannot be quoted this product, and open quotations with it cannot be accepted.</p>
          <button disabled={actions.restore.isPending} onClick={() => actions.restore.mutate(product.row_version)}>
            Restore
          </button>
        </>
      ) : (
        <>
          <p className="muted small">
            Archive a product you no longer sell. It disappears from search and quotations;
            its history stays.
          </p>
          <div className="actions">
            <button
              className="secondary"
              disabled={actions.archive.isPending}
              onClick={() => actions.archive.mutate(product.row_version)}
            >
              Archive
            </button>
            <button
              className="secondary"
              disabled={actions.remove.isPending}
              onClick={() => actions.remove.mutate(undefined, { onSuccess: () => navigate("/catalogue") })}
            >
              Delete
            </button>
          </div>
        </>
      )}
      <ErrorMessage message={actions.problem} />
    </section>
  );
}
