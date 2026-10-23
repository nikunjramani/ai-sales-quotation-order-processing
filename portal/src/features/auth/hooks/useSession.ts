import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authRepository } from "../api/authRepository";

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

export function useLogin() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: authRepository.devLogin,
    onSuccess: (session) => client.setQueryData(authKeys.session, session),
  });
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
