import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useTenantId } from "@/features/tenant";

import { quotationRepository } from "../api/quotationRepository";
import type { DecisionRequest, QuotationStatus, RevisionRequest } from "../model/types";
import { quotationKeys } from "./queryKeys";

/** `enabled: false` skips the request (the Home page only loads what the person may see). */
export function useQuotationList(statuses: readonly QuotationStatus[], { enabled = true } = {}) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: quotationKeys.list(tenantId, statuses),
    queryFn: () => quotationRepository.list(tenantId, statuses),
    enabled,
  });
}

export function useQuotation(quotationId: string) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: quotationKeys.detail(tenantId, quotationId),
    queryFn: () => quotationRepository.get(tenantId, quotationId),
  });
}

/** Any change (or conflict) refreshes this tenant's quotation lists and details. */
function useRefreshQuotations() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: quotationKeys.all(tenantId) });
}

export function useDecideQuotation() {
  const tenantId = useTenantId();
  const refresh = useRefreshQuotations();
  return useMutation({
    mutationFn: ({ taskId, request }: { taskId: string; request: DecisionRequest }) =>
      quotationRepository.decide(tenantId, taskId, request),
    onSettled: refresh,
  });
}

export function useReviseQuotation() {
  const tenantId = useTenantId();
  const refresh = useRefreshQuotations();
  return useMutation({
    mutationFn: ({ quotationId, request }: { quotationId: string; request: RevisionRequest }) =>
      quotationRepository.revise(tenantId, quotationId, request),
    onSuccess: refresh,
  });
}
