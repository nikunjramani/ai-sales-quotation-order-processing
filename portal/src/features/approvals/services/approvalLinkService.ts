// Service: pure rules for the signed approval link page. No React, no HTTP.

import type { ApprovalAction, ApprovalLink } from "../model/types";

export const ACTION_LABEL: Record<ApprovalAction, string> = {
  approve: "Approve",
  reject: "Reject",
  request_revision: "Request a revision",
};

const DONE: Record<ApprovalAction, string> = {
  approve: "approved",
  reject: "rejected",
  request_revision: "sent back for a revision",
};

/** What the page says when the request can no longer be decided here. */
export function stateText(link: ApprovalLink): string | null {
  if (link.state === "decided") {
    return `${link.number} version ${link.version} was already ${
      link.decided ? DONE[link.decided] : "decided"
    }.`;
  }
  if (link.state === "changed") {
    return `${link.number} has changed. You will get the new version to review.`;
  }
  if (link.state === "expired") {
    return "This approval link has expired or was already used. Please decide in the portal.";
  }
  return null;
}

/** Reject and revise need a reason (the approval record requires one). */
export function needsReason(action: ApprovalAction): boolean {
  return action !== "approve";
}

export function recordedText(action: ApprovalAction, link: ApprovalLink): string {
  return `${link.number} version ${link.version} ${DONE[action]}.`;
}
