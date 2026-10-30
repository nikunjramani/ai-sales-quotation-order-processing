import type { RouteObject } from "react-router";

import { HomePage } from "./ui/pages/HomePage";

// The Home page: what needs the person now (ADR 0025).
export const homeRoutes: RouteObject[] = [{ path: "home", element: <HomePage /> }];
