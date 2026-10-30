import { useCurrentTenant } from "@/features/tenant";
import { dateTime } from "@/shared/lib/format";
import { ErrorMessage } from "@/shared/ui/QueryState";

import { useCatalogueSync } from "../../hooks/useCatalogue";

/**
 * When products are copied from the business's ERP (phase 6): when the last copy ran, what it
 * changed, what could not be copied (units without a name we know, other currencies...) and
 * "Sync now". Quotations always check prices and stock in the ERP itself.
 */
export function CatalogueSyncPanel() {
  const { can } = useCurrentTenant();
  const { query, syncNow } = useCatalogueSync();
  const status = query.data;
  if (!status?.synced) return null;
  const run = status.latest;
  const counts = run?.counts;
  return (
    <section className="card">
      <h2>Copy from your ERP</h2>
      <p className="muted small">
        Copied every {status.every_minutes} minutes for searching; quotations check prices and
        stock in the ERP itself.
      </p>
      {!run && <p>The first copy has not run yet.</p>}
      {run?.status === "running" && <p>Copying now (started {dateTime(run.started_at)})…</p>}
      {run?.status === "succeeded" && run.finished_at && (
        <p>
          Last copied {dateTime(run.finished_at)}
          {counts && (
            <>
              : {counts.created ?? 0} new, {counts.updated ?? 0} changed, {counts.archived ?? 0}{" "}
              no longer offered, {counts.prices_added ?? 0} prices and {counts.stock_added ?? 0}{" "}
              stock counts updated
            </>
          )}
          .
        </p>
      )}
      {run?.status === "failed" && (
        <p className="card warn">
          The last copy failed{run.finished_at ? ` (${dateTime(run.finished_at)})` : ""}: {run.error}.
          The previous copy is still used.
        </p>
      )}
      {run?.next_run_at && <p className="muted small">Next copy: {dateTime(run.next_run_at)}</p>}
      {run && run.issues.length > 0 && (
        <details>
          <summary>{run.issues.length} things were not copied</summary>
          <ul className="plain">
            {run.issues.map((issue, index) => (
              <li key={`${issue.code}-${issue.sku ?? ""}-${index}`}>
                {issue.sku && <code>{issue.sku}</code>} {issue.message}
              </li>
            ))}
          </ul>
        </details>
      )}
      {can("catalogue:manage") && (
        <button
          className="secondary"
          disabled={syncNow.isPending || run?.status === "running"}
          onClick={() => syncNow.mutate()}
        >
          Sync now
        </button>
      )}
      {syncNow.data && !syncNow.data.queued && (
        <p className="muted small">A copy is already waiting to run.</p>
      )}
      <ErrorMessage message={syncNow.error?.message} />
    </section>
  );
}
