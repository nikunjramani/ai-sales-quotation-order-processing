import { http, tenantPath } from "@/shared/api/httpClient";

import type { EnquirySummary } from "../model/types";

export const enquiryRepository = {
  list: (tenantId: string, statuses: readonly string[]) =>
    http<EnquirySummary[]>(tenantPath(tenantId, "/enquiries"), { query: { status: [...statuses] } }),
};
