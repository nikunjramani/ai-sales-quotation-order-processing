import type { RouteObject } from "react-router";

import { LoginPage } from "./ui/LoginPage";

/** Public screens (no session needed). */
export const authRoutes: RouteObject[] = [{ path: "login", element: <LoginPage /> }];
