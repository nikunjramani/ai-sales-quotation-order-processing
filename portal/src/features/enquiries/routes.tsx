import type { RouteObject } from "react-router";

import { EnquiryListPage } from "./ui/pages/EnquiryListPage";

export const enquiryRoutes: RouteObject[] = [{ path: "enquiries", element: <EnquiryListPage /> }];
