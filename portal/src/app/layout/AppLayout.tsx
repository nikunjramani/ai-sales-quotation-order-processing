import { Outlet } from "react-router";

import { RequireSession } from "@/features/auth";
import { useCurrentTenant } from "@/features/tenant";

import { TopBar } from "./TopBar";

/** Frame for every signed-in screen. Pages render only when a business is selected. */
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
  if (!tenant) return <p className="notice">You are not a member of any business.</p>;
  // key: switching business remounts the pages, so no state from the previous one leaks over.
  return <Outlet key={tenant.tenant_id} />;
}
