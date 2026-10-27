import { http, tenantPath } from "@/shared/api/httpClient";

import type { Binding, Connection, Enrollment } from "../model/types";

export const connectionRepository = {
  list: (tenantId: string) =>
    http<Connection[]>(tenantPath(tenantId, "/connections")),

  bindings: (tenantId: string) =>
    http<Binding[]>(tenantPath(tenantId, "/channel-bindings")),

  /** A one-time code that links an account on this connection only. */
  startEnrollment: (tenantId: string, connectionId: string) =>
    http<Enrollment>(
      tenantPath(
        tenantId,
        `/connections/${encodeURIComponent(connectionId)}/enrollments`,
      ),
      { method: "POST" },
    ),

  revoke: (tenantId: string, bindingId: string) =>
    http<void>(
      tenantPath(
        tenantId,
        `/channel-bindings/${encodeURIComponent(bindingId)}`,
      ),
      {
        method: "DELETE",
      },
    ),
};
