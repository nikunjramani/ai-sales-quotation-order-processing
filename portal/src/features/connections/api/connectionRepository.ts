import { apiUrl, http, tenantPath } from "@/shared/api/httpClient";

import type {
  AvailableTool,
  Binding,
  Connection,
  ConnectionTest,
  EnableResult,
  Enrollment,
} from "../model/types";

const one = (connectionId: string, rest = "") =>
  `/connections/${encodeURIComponent(connectionId)}${rest}`;

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

  /** One-click tools (phase 5): create what the business needs, maybe one step left. */
  enable: (tenantId: string, providerKey: string, acceptCosts: boolean) =>
    http<EnableResult>(tenantPath(tenantId, "/connections/enable"), {
      method: "POST",
      body: { provider_key: providerKey, accept_costs: acceptCosts },
    }),

  /** The data a step returned (a form's answers, a pop-up's result). */
  resume: (
    tenantId: string,
    connectionId: string,
    actionId: string,
    submission: Record<string, unknown>,
  ) =>
    http<EnableResult>(
      tenantPath(tenantId, one(connectionId, `/actions/${encodeURIComponent(actionId)}`)),
      { method: "POST", body: { submission } },
    ),

  /** Address of a provider-hosted setup page, opened by the browser itself. */
  providerPageUrl: (tenantId: string, connectionId: string, actionId: string) =>
    apiUrl(
      `/tenants/${encodeURIComponent(tenantId)}` +
        one(connectionId, `/actions/${encodeURIComponent(actionId)}/page`),
    ),

  test: (tenantId: string, connectionId: string) =>
    http<ConnectionTest>(tenantPath(tenantId, one(connectionId, "/test")), {
      method: "POST",
    }),

  disable: (tenantId: string, connectionId: string) =>
    http<{ steps: string[] }>(tenantPath(tenantId, one(connectionId, "/disable")), {
      method: "POST",
    }),

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
