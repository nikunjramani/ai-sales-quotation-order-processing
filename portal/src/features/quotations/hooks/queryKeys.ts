import type { QuotationStatus } from "../model/types";

// Cache keys for quotation server state. Everything is scoped by tenant, so switching business
// never shows another business's cached data.
export const quotationKeys = {
  all: (tenantId: string) => ["tenants", tenantId, "quotations"] as const,
  list: (tenantId: string, statuses: readonly QuotationStatus[]) =>
    [...quotationKeys.all(tenantId), "list", [...statuses]] as const,
  detail: (tenantId: string, quotationId: string) =>
    [...quotationKeys.all(tenantId), "detail", quotationId] as const,
  delivery: (tenantId: string, quotationId: string) =>
    [...quotationKeys.all(tenantId), "delivery", quotationId] as const,
  customer: (tenantId: string, quotationId: string) =>
    [...quotationKeys.all(tenantId), "customer", quotationId] as const,
};
