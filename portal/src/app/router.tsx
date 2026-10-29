import { createHashRouter } from "react-router";

import { accountPublicRoutes, accountRoutes } from "@/features/account";
import { approvalRoutes } from "@/features/approvals";
import { businessRoutes, businessStartRoutes } from "@/features/business";
import { catalogueRoutes } from "@/features/catalogue";
import { connectionRoutes } from "@/features/connections";
import { conversationRoutes } from "@/features/conversations";
import { enquiryRoutes } from "@/features/enquiries";
import { quotationRoutes } from "@/features/quotations";

import { AppLayout, HomeRedirect, SignedInLayout } from "./layout/AppLayout";
import { NotFoundPage } from "./layout/NotFoundPage";

// The route table only combines what each feature exports. Adding a screen to an existing
// feature needs no change here; a new feature adds one line.
//
// Hash URLs (#/quotations) keep the portal plain static files: no server routing is needed,
// whether served by the API at /portal/ or from static hosting later.
export function createRouter() {
  return createHashRouter([
    // No session needed (sign-in, sign-up and the pages email links open).
    ...accountPublicRoutes,
    // The signed approval link from a message asks for sign-in itself (phase 5).
    ...approvalRoutes,
    // Signed in, with or without a business (profile, create a business).
    { element: <SignedInLayout />, children: [...accountRoutes, ...businessStartRoutes] },
    // Inside the current business.
    {
      path: "/",
      element: <AppLayout />,
      children: [
        { index: true, element: <HomeRedirect /> },
        ...quotationRoutes,
        ...enquiryRoutes,
        ...conversationRoutes,
        ...catalogueRoutes,
        ...connectionRoutes,
        ...businessRoutes,
        { path: "*", element: <NotFoundPage /> },
      ],
    },
  ]);
}
