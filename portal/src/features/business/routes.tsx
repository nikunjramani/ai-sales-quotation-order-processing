import type { RouteObject } from "react-router";
import { Navigate } from "react-router";

import { ApiKeysPage } from "./ui/pages/ApiKeysPage";
import { BusinessSettingsPage } from "./ui/pages/BusinessSettingsPage";
import { CreateBusinessPage } from "./ui/pages/CreateBusinessPage";
import { MembersPage } from "./ui/pages/MembersPage";
import { PricingSettingsPage } from "./ui/pages/PricingSettingsPage";
import { SetupPage } from "./ui/pages/SetupPage";
import { StartPage } from "./ui/pages/StartPage";

/** Signed in, no business needed yet. */
export const businessStartRoutes: RouteObject[] = [
  { path: "start", element: <StartPage /> },
  { path: "businesses/new", element: <CreateBusinessPage /> },
];

/** Inside the current business. */
export const businessRoutes: RouteObject[] = [
  { path: "setup", element: <SetupPage /> },
  { path: "settings", element: <Navigate to="/settings/business" replace /> },
  { path: "settings/business", element: <BusinessSettingsPage /> },
  { path: "settings/pricing", element: <PricingSettingsPage /> },
  { path: "settings/members", element: <MembersPage /> },
  { path: "settings/api-keys", element: <ApiKeysPage /> },
];
