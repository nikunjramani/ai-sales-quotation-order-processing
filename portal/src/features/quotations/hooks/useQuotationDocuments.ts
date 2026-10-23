import { useQuery } from "@tanstack/react-query";

import { useTenantId } from "@/features/tenant";

import { quotationRepository } from "../api/quotationRepository";
import type { QuotationStatus } from "../model/types";
import { deliveryInProgress } from "../services/deliveryService";
import { quotationKeys } from "./queryKeys";

const POLL_MS = 3000;

/**
 * Approved document and delivery status. Only approved quotations have one; while the worker is
 * still rendering or delivering, it is re-fetched every few seconds until the outcome is final.
 */
export function useQuotationDelivery(quotationId: string, status: QuotationStatus) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: quotationKeys.delivery(tenantId, quotationId),
    queryFn: () => quotationRepository.delivery(tenantId, quotationId),
    enabled: status === "approved",
    refetchInterval: (query) => (deliveryInProgress(query.state.data) ? POLL_MS : false),
  });
}

/** Download links for this tenant's quotation PDFs. */
export function useDocumentLinks(quotationId: string) {
  const tenantId = useTenantId();
  return {
    preview: (version: number) =>
      quotationRepository.previewPdfUrl(tenantId, quotationId, version),
    approved: quotationRepository.approvedPdfUrl(tenantId, quotationId),
  };
}
