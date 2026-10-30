import type { RouteObject } from "react-router";
import { Navigate } from "react-router";

import { useCurrentTenant } from "@/features/tenant";

import { IntegrationsPage } from "./ui/pages/IntegrationsPage";

/** Settings > Integrations (ADR 0025): mounted by the app under its settings frame. */
export const connectionSettingsRoutes: RouteObject[] = [
  { path: "integrations", element: <IntegrationsPage /> },
];

/**
 * The old "Apps & channels" (and pre-phase-1 "Channels") addresses: administrators go to
 * Settings > Integrations; managers to their profile, where they link their own account.
 */
function OldConnectionsPage() {
  const { can } = useCurrentTenant();
  return <Navigate to={can("integrations:manage") ? "/settings/integrations" : "/profile"} replace />;
}

export const connectionRoutes: RouteObject[] = [
  { path: "connections", element: <OldConnectionsPage /> },
  { path: "channels", element: <OldConnectionsPage /> },
];
