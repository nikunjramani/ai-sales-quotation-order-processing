import { useQuery } from "@tanstack/react-query";

import { useTenantId } from "@/features/tenant";

import { enquiryRepository } from "../api/enquiryRepository";

export const enquiryKeys = {
  list: (tenantId: string, statuses: readonly string[]) =>
    ["tenants", tenantId, "enquiries", "list", [...statuses]] as const,
};

export function useEnquiryList(statuses: readonly string[], { enabled = true } = {}) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: enquiryKeys.list(tenantId, statuses),
    queryFn: () => enquiryRepository.list(tenantId, statuses),
    enabled,
  });
}
