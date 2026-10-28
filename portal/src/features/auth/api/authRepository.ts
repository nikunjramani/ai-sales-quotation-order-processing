import { http, isApiError, setCsrfToken } from "@/shared/api/httpClient";

import type { AuthConfig, Session } from "../model/types";

// Repository: HTTP calls for the current session. It also keeps the CSRF token in sync,
// because every session the server returns carries the token for later changes. Signing in
// (password or dev login) lives in the account feature.
export const authRepository = {
  config: () => http<AuthConfig>("/auth/config"),

  /** The current session, or null when nobody is signed in. */
  async session(): Promise<Session | null> {
    try {
      const session = await http<Session>("/auth/session");
      setCsrfToken(session.csrf_token);
      return session;
    } catch (error) {
      if (isApiError(error, 401)) {
        setCsrfToken(null);
        return null;
      }
      throw error;
    }
  },

  async logout(): Promise<void> {
    try {
      await http<void>("/auth/logout", { method: "POST" });
    } finally {
      setCsrfToken(null);
    }
  },
};
