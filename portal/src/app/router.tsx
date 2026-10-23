import { createHashRouter, Navigate } from "react-router";

import { authRoutes } from "@/features/auth";
import { channelRoutes } from "@/features/channels";
import { enquiryRoutes } from "@/features/enquiries";
import { quotationRoutes } from "@/features/quotations";

import { AppLayout } from "./layout/AppLayout";
import { NotFoundPage } from "./layout/NotFoundPage";

// The route table only combines what each feature exports. Adding a screen to an existing
// feature needs no change here; a new feature adds one line.
//
// Hash URLs (#/quotations) keep the portal plain static files: no server routing is needed,
// whether served by the API at /portal/ or from static hosting later.
export function createRouter() {
  return createHashRouter([
    ...authRoutes,
    {
      path: "/",
      element: <AppLayout />,
      children: [
        { index: true, element: <Navigate to="/quotations" replace /> },
        ...quotationRoutes,
        ...enquiryRoutes,
        ...channelRoutes,
        { path: "*", element: <NotFoundPage /> },
      ],
    },
  ]);
}
