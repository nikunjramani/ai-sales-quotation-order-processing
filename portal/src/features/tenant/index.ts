// Public API of the tenant feature (which business the person is working in).
export { useCurrentTenant, useTenantId, type CurrentTenant } from "./hooks/useCurrentTenant";
export { useTenantStore } from "./store/tenantStore";
export { TenantSwitcher } from "./ui/TenantSwitcher";
