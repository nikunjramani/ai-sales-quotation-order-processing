import { useSession, type Permission, type TenantInfo } from "@/features/auth";

import { useTenantStore } from "../store/tenantStore";

export interface CurrentTenant {
  tenant: TenantInfo | null;
  tenants: TenantInfo[];
  selectTenant: (tenantId: string) => void;
  /** UI hint only (show or hide a button); the server re-checks every action. */
  can: (permission: Permission) => boolean;
}

/** The business being worked in: the stored choice if still valid, else the first membership. */
export function useCurrentTenant(): CurrentTenant {
  const session = useSession();
  const selectedId = useTenantStore((state) => state.selectedTenantId);
  const selectTenant = useTenantStore((state) => state.selectTenant);
  const tenants = session.data?.tenants ?? [];
  const tenant = tenants.find((item) => item.tenant_id === selectedId) ?? tenants[0] ?? null;
  return {
    tenant,
    tenants,
    selectTenant,
    can: (permission) => tenant?.permissions.includes(permission) ?? false,
  };
}

/** For pages under the app layout, which only renders them when a tenant exists. */
export function useTenantId(): string {
  const { tenant } = useCurrentTenant();
  if (!tenant) throw new Error("useTenantId used outside a tenant-scoped page");
  return tenant.tenant_id;
}
