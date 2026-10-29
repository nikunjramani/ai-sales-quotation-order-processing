import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { newCommandId } from "@/shared/lib/commandId";

import { approvalLinkRepository } from "../api/approvalLinkRepository";
import type { ApprovalAction } from "../model/types";

const linkKey = (token: string) => ["approval-links", token] as const;

/** The request behind a signed link; only asked once the person is signed in. */
export function useApprovalLink(token: string, signedIn: boolean) {
  return useQuery({
    queryKey: linkKey(token),
    queryFn: () => approvalLinkRepository.get(token),
    enabled: signedIn && token.length > 0,
    retry: false,
  });
}

/** One click decides; a retry of the same click reuses its command ID (applied once). */
export function useDecideByLink(token: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      action: ApprovalAction;
      contentSha256: string;
      reason?: string;
      commandId?: string;
    }) =>
      approvalLinkRepository.decide(token, {
        command_id: input.commandId ?? newCommandId(),
        action: input.action,
        content_sha256: input.contentSha256,
        reason: input.reason,
      }),
    onSettled: () => client.invalidateQueries({ queryKey: linkKey(token) }),
  });
}
