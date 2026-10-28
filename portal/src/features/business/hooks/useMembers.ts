import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";

import { useSessionCache } from "@/features/auth";
import { useTenantId } from "@/features/tenant";

import { membersRepository } from "../api/membersRepository";
import { businessKeys } from "./queryKeys";

export function useMembers(enabled = true) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: businessKeys.members(tenantId),
    queryFn: () => membersRepository.list(tenantId),
    enabled,
  });
}

function useRefreshMembers() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  return () =>
    Promise.all([
      client.invalidateQueries({ queryKey: businessKeys.members(tenantId) }),
      client.invalidateQueries({ queryKey: businessKeys.invitations(tenantId) }),
      client.invalidateQueries({ queryKey: businessKeys.setup(tenantId) }),
    ]);
}

export function useChangeRoles() {
  const tenantId = useTenantId();
  const refresh = useRefreshMembers();
  const cache = useSessionCache();
  return useMutation({
    mutationFn: ({ userId, roles }: { userId: string; roles: string[] }) =>
      membersRepository.changeRoles(tenantId, userId, roles),
    onSettled: async () => {
      await refresh();
      await cache.refresh(); // your own roles may have changed
    },
  });
}

export function useRemoveMember() {
  const tenantId = useTenantId();
  const refresh = useRefreshMembers();
  return useMutation({
    mutationFn: (userId: string) => membersRepository.remove(tenantId, userId),
    onSettled: refresh,
  });
}

/** Leaving a business yourself (Q22): afterwards the session no longer lists it. */
export function useLeaveBusiness() {
  const cache = useSessionCache();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: ({ tenantId, userId }: { tenantId: string; userId: string }) =>
      membersRepository.remove(tenantId, userId),
    onSuccess: async () => {
      await cache.refresh();
      navigate("/", { replace: true });
    },
  });
}

export function useInvitations(enabled = true) {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: businessKeys.invitations(tenantId),
    queryFn: () => membersRepository.invitations(tenantId),
    enabled,
  });
}

export function useInvite() {
  const tenantId = useTenantId();
  const refresh = useRefreshMembers();
  return useMutation({
    mutationFn: ({ email, roles }: { email: string; roles: string[] }) =>
      membersRepository.invite(tenantId, email, roles),
    onSuccess: refresh,
  });
}

export function useInvitationActions() {
  const tenantId = useTenantId();
  const refresh = useRefreshMembers();
  const resend = useMutation({
    mutationFn: (invitationId: string) => membersRepository.resend(tenantId, invitationId),
    onSettled: refresh,
  });
  const revoke = useMutation({
    mutationFn: (invitationId: string) => membersRepository.revoke(tenantId, invitationId),
    onSettled: refresh,
  });
  return { resend, revoke };
}
