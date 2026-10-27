import { Navigate, Outlet } from "react-router";

import { VerifyEmailBanner } from "@/features/account";
import { RequireSession } from "@/features/auth";
import { StatusBanner } from "@/features/business";
import { useCurrentTenant } from "@/features/tenant";

import { TopBar } from "./TopBar";

/** Frame for signed-in screens that do not need a business (profile, create a business). */
export function SignedInLayout() {
  return (
    <RequireSession>
      <TopBar />
      <main>
        <VerifyEmailBanner />
        <Outlet />
      </main>
    </RequireSession>
  );
}

/** Frame for every screen inside a business. Without one, the person starts at /start. */
export function AppLayout() {
  return (
    <RequireSession>
      <TopBar />
      <main>
        <TenantGate />
      </main>
    </RequireSession>
  );
}

function TenantGate() {
  const { tenant } = useCurrentTenant();
  if (!tenant) return <Navigate to="/start" replace />;
  // key: switching business remounts the pages, so no state from the previous one leaks over.
  return (
    <>
      <StatusBanner />
      <Outlet key={tenant.tenant_id} />
    </>
  );
}

/** Home: a business in setup opens its checklist (for those who can finish it), else quotations. */
export function HomeRedirect() {
  const { tenant, can } = useCurrentTenant();
  const setup = tenant?.status === "setting_up" && can("tenant:manage");
  return <Navigate to={setup ? "/setup" : "/quotations"} replace />;
}
