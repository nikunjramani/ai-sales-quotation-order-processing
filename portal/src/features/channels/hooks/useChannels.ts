import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useTenantId } from "@/features/tenant";

import { channelRepository } from "../api/channelRepository";

export const channelKeys = {
  bindings: (tenantId: string) => ["tenants", tenantId, "channel-bindings"] as const,
};

export function useBindings() {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: channelKeys.bindings(tenantId),
    queryFn: () => channelRepository.bindings(tenantId),
  });
}

/** Returns the one-time code; linked accounts refresh when the code is used and the list reloads. */
export function useStartEnrollment() {
  const tenantId = useTenantId();
  return useMutation({
    mutationFn: (channel: string) => channelRepository.startEnrollment(tenantId, channel),
  });
}

export function useRevokeBinding() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  return useMutation({
    mutationFn: (bindingId: string) => channelRepository.revoke(tenantId, bindingId),
    onSettled: () => client.invalidateQueries({ queryKey: channelKeys.bindings(tenantId) }),
  });
}
