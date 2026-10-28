import { http, tenantPath } from "@/shared/api/httpClient";

import type { ApiKeySummary, NewApiKey } from "../model/types";

export const apiKeysRepository = {
  list: (tenantId: string) => http<ApiKeySummary[]>(tenantPath(tenantId, "/api-keys")),

  create: (tenantId: string, name: string) =>
    http<NewApiKey>(tenantPath(tenantId, "/api-keys"), { method: "POST", body: { name } }),

  revoke: (tenantId: string, keyId: string) =>
    http<void>(tenantPath(tenantId, `/api-keys/${encodeURIComponent(keyId)}`), {
      method: "DELETE",
    }),
};
