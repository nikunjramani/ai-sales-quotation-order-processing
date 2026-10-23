import { apiUrl, http, tenantPath } from "@/shared/api/httpClient";

import type {
  CustomerView,
  DecisionRequest,
  DeliveryOverview,
  QuotationDetail,
  QuotationStatus,
  QuotationSummary,
  RevisionRequest,
  RevisionResult,
  WithdrawalRequest,
} from "../model/types";

// Repository: the quotation endpoints, nothing else. No state, no business decisions.
export const quotationRepository = {
  list: (tenantId: string, statuses: readonly QuotationStatus[]) =>
    http<QuotationSummary[]>(tenantPath(tenantId, "/quotations"), {
      query: { status: [...statuses] },
    }),

  get: (tenantId: string, quotationId: string) =>
    http<QuotationDetail>(tenantPath(tenantId, `/quotations/${encodeURIComponent(quotationId)}`)),

  decide: (tenantId: string, taskId: string, request: DecisionRequest) =>
    http<unknown>(tenantPath(tenantId, `/approval-tasks/${encodeURIComponent(taskId)}/decision`), {
      method: "POST",
      body: request,
    }),

  revise: (tenantId: string, quotationId: string, request: RevisionRequest) =>
    http<RevisionResult>(
      tenantPath(tenantId, `/quotations/${encodeURIComponent(quotationId)}/revisions`),
      { method: "POST", body: request },
    ),

  delivery: (tenantId: string, quotationId: string) =>
    http<DeliveryOverview>(
      tenantPath(tenantId, `/quotations/${encodeURIComponent(quotationId)}/delivery`),
    ),

  customerView: (tenantId: string, quotationId: string) =>
    http<CustomerView>(
      tenantPath(tenantId, `/quotations/${encodeURIComponent(quotationId)}/customer`),
    ),

  withdraw: (tenantId: string, quotationId: string, request: WithdrawalRequest) =>
    http<unknown>(
      tenantPath(tenantId, `/quotations/${encodeURIComponent(quotationId)}/withdrawal`),
      { method: "POST", body: request },
    ),

  // PDFs are opened by the browser as downloads (the session cookie goes with them).
  previewPdfUrl: (tenantId: string, quotationId: string, version: number) =>
    apiUrl(
      tenantPath(
        tenantId,
        `/quotations/${encodeURIComponent(quotationId)}/versions/${version}/preview.pdf`,
      ),
    ),

  approvedPdfUrl: (tenantId: string, quotationId: string) =>
    apiUrl(tenantPath(tenantId, `/quotations/${encodeURIComponent(quotationId)}/document.pdf`)),
};
