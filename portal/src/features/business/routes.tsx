import type { RouteObject } from "react-router";

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
export const businessRoutes: RouteObject[] = [{ path: "setup", element: <SetupPage /> }];

/** Settings sections (ADR 0025): the app mounts them under its settings frame (/settings/...). */
export const businessSettingsRoutes: RouteObject[] = [
  { path: "business", element: <BusinessSettingsPage /> },
  { path: "pricing", element: <PricingSettingsPage /> },
  { path: "members", element: <MembersPage /> },
  { path: "api-keys", element: <ApiKeysPage /> },
];
