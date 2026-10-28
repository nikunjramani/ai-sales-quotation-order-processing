import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { setCsrfToken } from "@/shared/api/httpClient";

import { authRepository } from "../api/authRepository";
import type { Session } from "../model/types";

export const authKeys = {
  session: ["auth", "session"] as const,
  config: ["auth", "config"] as const,
};

/** Server state: who is signed in (null = nobody). Shared by every screen through the cache. */
export function useSession() {
  return useQuery({ queryKey: authKeys.session, queryFn: authRepository.session, staleTime: 60_000 });
}

export function useAuthConfig() {
  return useQuery({ queryKey: authKeys.config, queryFn: authRepository.config, staleTime: Infinity });
}

/**
 * For other features that change the session (signing in, creating or joining a business):
 * `set` stores a session the server just returned, `refresh` reloads it.
 */
export function useSessionCache() {
  const client = useQueryClient();
  return {
    set(session: Session) {
      setCsrfToken(session.csrf_token);
      client.setQueryData(authKeys.session, session);
    },
    refresh: () => client.invalidateQueries({ queryKey: authKeys.session }),
  };
}

export function useLogout() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: authRepository.logout,
    // Drop every cached business record so the next person sees nothing of the previous one.
    onSettled: () => {
      client.clear();
      client.setQueryData(authKeys.session, null);
    },
  });
}
