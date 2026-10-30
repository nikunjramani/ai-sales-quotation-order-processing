import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router";

import { EnquiryThread } from "@/features/conversations";
import { QuotationOrderPanel } from "@/features/orders";
import { useCurrentTenant } from "@/features/tenant";
import { QueryState } from "@/shared/ui/QueryState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

import { useQuotation } from "../../hooks/useQuotations";
import { currentVersion } from "../../services/quotationService";
import { CustomerPanel } from "../components/CustomerPanel";
import { DecisionPanel } from "../components/DecisionPanel";
import { DocumentPanel } from "../components/DocumentPanel";
import { PricingIssuesCard } from "../components/PricingIssuesCard";
import { QuotationHistory } from "../components/QuotationHistory";
import { RevisionForm } from "../components/RevisionForm";
import { VersionTable } from "../components/VersionTable";

/** Full review of one quotation: exact version content, exceptions, history and actions. */
export function QuotationDetailPage() {
  const { quotationId = "" } = useParams();
  const query = useQuotation(quotationId);
  const { can } = useCurrentTenant();
  const detail = query.data;
  const current = detail ? currentVersion(detail) : null;

  return (
    <article>
      <Link className="link" to="/quotations">
        <ArrowLeft size={18} aria-hidden="true" /> All quotes
      </Link>
      <QueryState isLoading={query.isLoading} error={query.error}>
        {detail && (
          <>
            <header className="title-row">
              <h1>
                {detail.summary.number}
                {current && <span className="muted"> · version {current.version}</span>}
              </h1>
              <StatusBadge status={detail.summary.status} />
            </header>
            <p className="muted">
              Customer reference: {detail.summary.customer_reference ?? "not given"}
            </p>
            <section className="card">
              <h2>Customer request</h2>
              {can("conversations:view") ? (
                // Every message of the enquiry, ours included (phase 4).
                <EnquiryThread enquiryId={detail.summary.enquiry_id} />
              ) : (
                <p className="quote">{detail.enquiry_text}</p>
              )}
            </section>
            <PricingIssuesCard issues={detail.pricing_issues} />
            {current && <VersionTable version={current} />}
            <DocumentPanel detail={detail} />
            <CustomerPanel quotationId={detail.summary.quotation_id} />
            <QuotationOrderPanel
              quotationId={detail.summary.quotation_id}
              accepted={detail.summary.status === "accepted"}
            />
            {detail.can_decide && detail.pending_task && (
              // key: a new task (new version) starts with a fresh form and command IDs.
              <DecisionPanel key={detail.pending_task.task_id} task={detail.pending_task} />
            )}
            {detail.pending_task && !detail.can_decide && (
              <p className="notice">
                Waiting for an approver. You cannot approve a version you created.
              </p>
            )}
            {detail.can_revise && (
              <RevisionForm key={detail.summary.current_version ?? 0} detail={detail} />
            )}
            <QuotationHistory detail={detail} />
          </>
        )}
      </QueryState>
    </article>
  );
}
