import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";

import { useSessionCache } from "@/features/auth";
import { useCurrentTenant, useTenantId } from "@/features/tenant";

import { businessRepository } from "../api/businessRepository";
import type { NewBusiness, PricingInput, ProfileInput } from "../model/types";
import { base64FromDataUrl, logoProblem } from "../services/logoFile";
import { businessKeys } from "./queryKeys";

/** Creates the business, then opens its setup (the new business becomes the current one). */
export function useCreateBusiness() {
  const cache = useSessionCache();
  const { selectTenant } = useCurrentTenant();
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (input: NewBusiness) => businessRepository.create(input),
    onSuccess: async ({ tenant_id }) => {
      await cache.refresh();
      selectTenant(tenant_id);
      navigate("/setup", { replace: true });
    },
  });
}

export function useBusinessSettings() {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: businessKeys.settings(tenantId),
    queryFn: () => businessRepository.settings(tenantId),
  });
}

/** After a change: the settings, the checklist and the session (name, status) reload. */
function useRefreshBusiness() {
  const tenantId = useTenantId();
  const client = useQueryClient();
  const cache = useSessionCache();
  return async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: businessKeys.settings(tenantId) }),
      client.invalidateQueries({ queryKey: businessKeys.pricing(tenantId) }),
      client.invalidateQueries({ queryKey: businessKeys.setup(tenantId) }),
      cache.refresh(),
    ]);
  };
}

export function useUpdateDetails() {
  const tenantId = useTenantId();
  const refresh = useRefreshBusiness();
  return useMutation({
    mutationFn: (input: { name: string; country: string; time_zone: string }) =>
      businessRepository.updateDetails(tenantId, input),
    onSuccess: refresh,
  });
}

export function useUpdateProfile() {
  const tenantId = useTenantId();
  const refresh = useRefreshBusiness();
  return useMutation({
    mutationFn: (input: ProfileInput) => businessRepository.updateProfile(tenantId, input),
    onSettled: refresh, // a 409 also reloads, so the next save uses the current version
  });
}

function readFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(base64FromDataUrl(String(reader.result)));
    reader.onerror = () => reject(new Error("The file could not be read"));
    reader.readAsDataURL(file);
  });
}

export function useLogo() {
  const tenantId = useTenantId();
  const refresh = useRefreshBusiness();
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const problem = logoProblem(file);
      if (problem) throw new Error(problem);
      await businessRepository.uploadLogo(tenantId, await readFile(file));
    },
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: () => businessRepository.removeLogo(tenantId),
    onSuccess: refresh,
  });
  return {
    upload,
    remove,
    url: (version: number) => businessRepository.logoUrl(tenantId, version),
  };
}

export function usePricing() {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: businessKeys.pricing(tenantId),
    queryFn: () => businessRepository.pricing(tenantId),
  });
}

export function useUpdatePricing() {
  const tenantId = useTenantId();
  const refresh = useRefreshBusiness();
  return useMutation({
    mutationFn: (input: PricingInput) => businessRepository.updatePricing(tenantId, input),
    onSettled: refresh,
  });
}

export function useSetupChecklist() {
  const tenantId = useTenantId();
  return useQuery({
    queryKey: businessKeys.setup(tenantId),
    queryFn: () => businessRepository.setup(tenantId),
  });
}

export function useGoLive() {
  const tenantId = useTenantId();
  const refresh = useRefreshBusiness();
  return useMutation({
    mutationFn: () => businessRepository.goLive(tenantId),
    onSettled: refresh,
  });
}
