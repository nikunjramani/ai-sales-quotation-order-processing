import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useTenantId } from "@/features/tenant";

import { apiKeysRepository } from "../api/apiKeysRepository";
import { businessKeys } from "./queryKeys";

export function useApiKeys() {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: businessKeys.apiKeys(tenantId),
    queryFn: () => apiKeysRepository.list(tenantId),
  });
}

/**
 * The new key's token lives only in this mutation's result, shown once in a dialog. It is never
 * put in the query cache, the store or browser storage; closing the dialog (reset) drops it.
 */
export function useCreateApiKey() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => apiKeysRepository.create(tenantId, name),
    onSettled: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: businessKeys.apiKeys(tenantId) }),
        client.invalidateQueries({ queryKey: businessKeys.setup(tenantId) }),
      ]),
  });
}

export function useRevokeApiKey() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) => apiKeysRepository.revoke(tenantId, keyId),
    onSettled: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: businessKeys.apiKeys(tenantId) }),
        client.invalidateQueries({ queryKey: businessKeys.setup(tenantId) }),
      ]),
  });
}
