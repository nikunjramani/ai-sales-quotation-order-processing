import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router";

import { useSession, useSessionCache } from "@/features/auth";
import { useCurrentTenant } from "@/features/tenant";
import { isApiError } from "@/shared/api/httpClient";

import { accountRepository } from "../api/accountRepository";
import { INVALID_LINK } from "../services/links";

/** Preview (no session needed) and accept (signed in with the invited address, Q9). */
export function useInvitation(token: string | null) {
  const session = useSession();
  const cache = useSessionCache();
  const { selectTenant } = useCurrentTenant();
  const navigate = useNavigate();
  const preview = useQuery({
    queryKey: ["invitation", token],
    queryFn: () => accountRepository.previewInvitation(token ?? ""),
    enabled: token !== null,
    retry: false,
    staleTime: Infinity,
  });
  const accept = useMutation({
    mutationFn: accountRepository.acceptInvitation,
    onSuccess: async ({ tenant_id }) => {
      await cache.refresh();
      selectTenant(tenant_id);
      navigate("/", { replace: true });
    },
  });
  let error: string | null = null;
  if (!token || preview.isError) error = INVALID_LINK;
  else if (isApiError(accept.error, 404)) {
    error = "This invitation cannot be used with this account. Sign in with the invited address.";
  } else if (accept.error) error = "Joining failed; try again.";
  return {
    preview: preview.data ?? null,
    loading: preview.isLoading,
    signedIn: Boolean(session.data),
    accept: () => token && accept.mutate(token),
    busy: accept.isPending,
    error,
  };
}
