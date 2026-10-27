import type { RouteObject } from "react-router";
import { Navigate } from "react-router";

import { ConnectionsPage } from "./ui/pages/ConnectionsPage";

export const connectionRoutes: RouteObject[] = [
  { path: "connections", element: <ConnectionsPage /> },
  // The page was called "Channels" before phase 1; old links still work.
  { path: "channels", element: <Navigate to="/connections" replace /> },
];
