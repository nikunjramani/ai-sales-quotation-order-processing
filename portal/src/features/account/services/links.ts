// Service: reading the single-use token from an email link. Links look like
// <portal>#/verify-email?token=...; the token is in the URL fragment, so it never reaches a
// server log. Pages read it once and then remove it from the address bar.

/** The token from a router search string ("?token=..."), or null. */
export function tokenFromSearch(search: string): string | null {
  const token = new URLSearchParams(search).get("token");
  return token && /^[A-Za-z0-9_-]{20,100}$/.test(token) ? token : null;
}

/** Shown after sign-up and "forgot password", whatever the server knows (no account leaks). */
export const CHECK_EMAIL =
  "If the address can be used, an email is on its way. Open the link in it to continue.";

export const INVALID_LINK = "This link is not valid any more. Ask for a new one.";

// Same plain names as the business feature's People page (ADR 0025).
export const ROLE_LABEL: Record<string, string> = {
  administrator: "Admin",
  sales_operator: "Sales",
  approver: "Manager",
  viewer: "View only",
};

export function roleText(roles: string[]): string {
  return roles.map((role) => ROLE_LABEL[role] ?? role).join(", ");
}
