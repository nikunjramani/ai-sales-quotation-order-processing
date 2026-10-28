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

export function useAvailableTools(enabled: boolean) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: [...connectionKeys.list(tenantId), "available"] as const,
    queryFn: () => connectionRepository.available(tenantId),
    enabled,
  });
}

/** Enable, configure, re-address and switch a hosted chat; the list reloads after each. */
export function useHostedChat() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  const refresh = () => client.invalidateQueries({ queryKey: connectionKeys.list(tenantId) });
  return {
    enable: useMutation({
      mutationFn: (providerKey: string) => connectionRepository.enableChat(tenantId, providerKey),
      onSettled: refresh,
    }),
    settings: useMutation({
      mutationFn: (input: { id: string; allowed_origins: string[]; greeting: string }) =>
        connectionRepository.chatSettings(tenantId, input.id, {
          allowed_origins: input.allowed_origins,
          greeting: input.greeting,
        }),
      onSettled: refresh,
    }),
    address: useMutation({
      mutationFn: (input: { id: string; handle: string }) =>
        connectionRepository.chatAddress(tenantId, input.id, input.handle),
      onSettled: refresh,
    }),
    active: useMutation({
      mutationFn: (input: { id: string; active: boolean }) =>
        connectionRepository.chatActive(tenantId, input.id, input.active),
      onSettled: refresh,
    }),
  };
}
