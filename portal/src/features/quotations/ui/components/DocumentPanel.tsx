import { QueryState } from "@/shared/ui/QueryState";
import { fileSize } from "@/shared/lib/format";

import { useDocumentLinks, useQuotationDelivery } from "../../hooks/useQuotationDocuments";
import type { QuotationDetail } from "../../model/types";
import { shortHash } from "../../services/deliveryService";
import { currentVersion } from "../../services/quotationService";
import { DeliveryList } from "./DeliveryList";

/** PDF preview of the current version, and for approved quotations the issued PDF and delivery. */
export function DocumentPanel({ detail }: { detail: QuotationDetail }) {
  const { quotation_id: quotationId, status } = detail.summary;
  const links = useDocumentLinks(quotationId);
  const delivery = useQuotationDelivery(quotationId, status);
  const current = currentVersion(detail);
  if (!current) return null;
  const document = delivery.data?.document ?? null;

  return (
    <section className="card">
      <h2>Quotation PDF</h2>
      {status !== "approved" && (
        <p>
          <a className="link" href={links.preview(current.version)} download>
            Preview PDF of version {current.version}
          </a>
          <span className="muted small"> Marked “not an offer”; only approved PDFs are sent.</span>
        </p>
      )}
      {status === "approved" && (
        <QueryState isLoading={delivery.isLoading} error={delivery.error}>
          {document ? (
            <p>
              <a className="button primary" href={links.approved} download>
                Download approved PDF
              </a>{" "}
              <span className="muted small" title={document.sha256}>
                Version {document.version} · {fileSize(document.size_bytes)} · SHA-256{" "}
                {shortHash(document.sha256)}
              </span>
            </p>
          ) : (
            <p className="muted">The approved PDF is being prepared…</p>
          )}
          <h3>Delivery to the customer</h3>
          <DeliveryList deliveries={delivery.data?.deliveries ?? []} />
        </QueryState>
      )}
    </section>
  );
}
