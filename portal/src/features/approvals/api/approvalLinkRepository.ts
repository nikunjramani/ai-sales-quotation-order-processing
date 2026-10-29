import { http } from "@/shared/api/httpClient";

import type { ApprovalAction, ApprovalLink, LinkDecision } from "../model/types";

const path = (token: string) => `/approval-links/${encodeURIComponent(token)}`;

export const approvalLinkRepository = {
  get: (token: string) => http<ApprovalLink>(path(token)),

  decide: (
    token: string,
    input: { command_id: string; action: ApprovalAction; content_sha256: string; reason?: string },
  ) => http<LinkDecision>(`${path(token)}/decision`, { method: "POST", body: input }),
};
