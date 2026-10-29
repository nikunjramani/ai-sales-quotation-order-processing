import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useTenantId } from "@/features/tenant";

import { connectionRepository } from "../api/connectionRepository";
import type { EnableResult } from "../model/types";
import { pollInterval } from "../services/connectionService";
import { useConnectionSetup } from "../store/connectionSetup";

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
    // A tool being set up finishes in the tool (e.g. the business adds our bot): ask again.
    refetchInterval: (query) => pollInterval(query.state.data),
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

/** One-click tools (phase 5): Enable, a step's data, Test and Disable; the list reloads. */
export function useOneClick() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  const remember = useConnectionSetup((state) => state.remember);
  const refresh = () => client.invalidateQueries({ queryKey: connectionKeys.list(tenantId) });
  const keepOnce = (result: EnableResult) => {
    if (result.pending && Object.keys(result.pending.once).length > 0) {
      remember(result.connection.connection_id, result.pending.once);
    }
  };
  return {
    enable: useMutation({
      mutationFn: (input: { providerKey: string; acceptCosts: boolean }) =>
        connectionRepository.enable(tenantId, input.providerKey, input.acceptCosts),
      onSuccess: keepOnce,
      onSettled: refresh,
    }),
    resume: useMutation({
      mutationFn: (input: {
        connectionId: string;
        actionId: string;
        submission: Record<string, unknown>;
      }) =>
        connectionRepository.resume(tenantId, input.connectionId, input.actionId, input.submission),
      onSuccess: keepOnce,
      onSettled: refresh,
    }),
    test: useMutation({
      mutationFn: (connectionId: string) => connectionRepository.test(tenantId, connectionId),
    }),
    disable: useMutation({
      mutationFn: (connectionId: string) => connectionRepository.disable(tenantId, connectionId),
      onSettled: refresh,
    }),
    pageUrl: (connectionId: string, actionId: string) =>
      connectionRepository.providerPageUrl(tenantId, connectionId, actionId),
  };
}

/** Which tool's Enable dialog is open (client state). */
export function useEnableDialog() {
  const enabling = useConnectionSetup((state) => state.enabling);
  const open = useConnectionSetup((state) => state.open);
  const close = useConnectionSetup((state) => state.close);
  return { enabling, open, close };
}

/** The one-time values (a link code) this browser got when the tool was enabled. */
export function useOnceValues(connectionId: string): Record<string, string> | undefined {
  return useConnectionSetup((state) => state.once[connectionId]);
}
