// Service: member rules as UI hints. The database enforces them again under a lock.

import type { Member } from "../model/types";

export const PEOPLE_ROLES = ["administrator", "sales_operator", "approver", "viewer"] as const;

export const ROLE_LABEL: Record<string, string> = {
  administrator: "Administrator",
  sales_operator: "Sales operator",
  approver: "Approver",
  viewer: "Viewer",
};

/** True when this member is the only administrator (cannot be removed or demoted). */
export function isLastAdministrator(members: Member[], member: Member): boolean {
  const administrators = members.filter((item) => item.roles.includes("administrator"));
  return administrators.length === 1 && administrators[0]?.user_id === member.user_id;
}

export function toggleRole(roles: string[], role: string): string[] {
  return roles.includes(role) ? roles.filter((item) => item !== role) : [...roles, role].sort();
}
