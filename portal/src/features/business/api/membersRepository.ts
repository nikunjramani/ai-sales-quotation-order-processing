import { http, tenantPath } from "@/shared/api/httpClient";

import type { Invitation, Member } from "../model/types";

const path = encodeURIComponent;

export const membersRepository = {
  list: (tenantId: string) => http<Member[]>(tenantPath(tenantId, "/members")),

  changeRoles: (tenantId: string, userId: string, roles: string[]) =>
    http<void>(tenantPath(tenantId, `/members/${path(userId)}/roles`), {
      method: "PUT",
      body: { roles },
    }),

  remove: (tenantId: string, userId: string) =>
    http<void>(tenantPath(tenantId, `/members/${path(userId)}`), { method: "DELETE" }),

  invitations: (tenantId: string) => http<Invitation[]>(tenantPath(tenantId, "/invitations")),

  /** The link exists only in the email; the answer never contains it. */
  invite: (tenantId: string, email: string, roles: string[]) =>
    http<{ invitation_id: string }>(tenantPath(tenantId, "/invitations"), {
      method: "POST",
      body: { email, roles },
    }),

  resend: (tenantId: string, invitationId: string) =>
    http<void>(tenantPath(tenantId, `/invitations/${path(invitationId)}/resend`), {
      method: "POST",
    }),

  revoke: (tenantId: string, invitationId: string) =>
    http<void>(tenantPath(tenantId, `/invitations/${path(invitationId)}`), { method: "DELETE" }),
};
