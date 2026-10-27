import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useTenantId } from "@/features/tenant";

import { connectionRepository } from "../api/connectionRepository";

export const connectionKeys = {
  list: (tenantId: string) => ["tenants", tenantId, "connections"] as const,
  bindings: (tenantId: string) =>
    ["tenants", tenantId, "channel-bindings"] as const,
};

export function useConnections(enabled = true) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: connectionKeys.list(tenantId),
    queryFn: () => connectionRepository.list(tenantId),
    enabled,
  });
}

export function useBindings() {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: connectionKeys.bindings(tenantId),
    queryFn: () => connectionRepository.bindings(tenantId),
  });
}

/** Returns the one-time code; the account list reloads once the code has been used. */
export function useStartEnrollment() {
  const tenantId = useTenantId();
  return useMutation({
    mutationFn: (connectionId: string) =>
      connectionRepository.startEnrollment(tenantId, connectionId),
  });
}

export function useRevokeBinding() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (bindingId: string) =>
      connectionRepository.revoke(tenantId, bindingId),
    onSettled: () =>
      client.invalidateQueries({ queryKey: connectionKeys.bindings(tenantId) }),
  });
}
