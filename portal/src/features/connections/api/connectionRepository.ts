import { http, tenantPath } from "@/shared/api/httpClient";

import type { AvailableTool, Binding, Connection, Enrollment } from "../model/types";

export const connectionRepository = {
  list: (tenantId: string) =>
    http<Connection[]>(tenantPath(tenantId, "/connections")),

  available: (tenantId: string) =>
    http<AvailableTool[]>(tenantPath(tenantId, "/connections/available")),

  enableChat: (tenantId: string, providerKey: string) =>
    http<Connection>(tenantPath(tenantId, "/connections/hosted-chat"), {
      method: "POST",
      body: { provider_key: providerKey },
    }),

  chatSettings: (
    tenantId: string,
    connectionId: string,
    settings: { allowed_origins?: string[]; greeting?: string },
  ) =>
    http<Connection>(
      tenantPath(tenantId, `/connections/${encodeURIComponent(connectionId)}/chat`),
      { method: "PATCH", body: settings },
    ),

  chatAddress: (tenantId: string, connectionId: string, handle: string) =>
    http<Connection>(
      tenantPath(tenantId, `/connections/${encodeURIComponent(connectionId)}/chat/address`),
      { method: "PUT", body: { handle } },
    ),

  chatActive: (tenantId: string, connectionId: string, active: boolean) =>
    http<Connection>(
      tenantPath(tenantId, `/connections/${encodeURIComponent(connectionId)}/chat/active`),
      { method: "PUT", body: { active } },
    ),

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
