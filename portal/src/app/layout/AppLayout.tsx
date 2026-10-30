import { Navigate, Outlet } from "react-router";

import { VerifyEmailBanner } from "@/features/account";
import { RequireSession } from "@/features/auth";
import { StatusBanner } from "@/features/business";
import { useCurrentTenant } from "@/features/tenant";

import { BottomNav, SideNav } from "./SideNav";
import { TopBar } from "./TopBar";

/** Frame for signed-in screens that do not need a business (profile, create a business). */
export function SignedInLayout() {
  return (
    <RequireSession>
      <div className="shell">
        <TopBar />
        <div className="shell-body">
          <SideNav />
          <main>
            <VerifyEmailBanner />
            <Outlet />
          </main>
        </div>
        <BottomNav />
      </div>
    </RequireSession>
  );
}

/**
 * Frame for every screen inside a business: the top bar, the menu (a sidebar on wide screens, a
 * bottom bar on phones) and the page. Without a business, the person starts at /start.
 */
export function AppLayout() {
  return (
    <RequireSession>
      <div className="shell">
        <TopBar />
        <div className="shell-body">
          <SideNav />
          <main>
            <TenantGate />
          </main>
        </div>
        <BottomNav />
      </div>
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

/** Start page: a business in setup opens its checklist (for those who can finish it), else Home. */
export function HomeRedirect() {
  const { tenant, can } = useCurrentTenant();
  const setup = tenant?.status === "setting_up" && can("tenant:manage");
  return <Navigate to={setup ? "/setup" : "/home"} replace />;
}
