import type { RouteObject } from "react-router";

import { ApproveLinkPage } from "./ui/pages/ApproveLinkPage";

/** Public route: the page itself asks for sign-in (the link opens from a message). */
export const approvalRoutes: RouteObject[] = [
  { path: "approve/:token", element: <ApproveLinkPage /> },
];
