import { http, tenantPath } from "@/shared/api/httpClient";

import type { Binding, Enrollment } from "../model/types";

export const channelRepository = {
  bindings: (tenantId: string) => http<Binding[]>(tenantPath(tenantId, "/channel-bindings")),

  startEnrollment: (tenantId: string, channel: string) =>
    http<Enrollment>(tenantPath(tenantId, "/channel-enrollments"), {
      method: "POST",
      body: { channel },
    }),

  revoke: (tenantId: string, bindingId: string) =>
    http<void>(tenantPath(tenantId, `/channel-bindings/${encodeURIComponent(bindingId)}`), {
      method: "DELETE",
    }),
};
