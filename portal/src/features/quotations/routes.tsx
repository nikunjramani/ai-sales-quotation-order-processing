import type { RouteObject } from "react-router";

import { QuotationDetailPage } from "./ui/pages/QuotationDetailPage";
import { QuotationListPage } from "./ui/pages/QuotationListPage";

// Screens of this feature. A new quotation screen = a new page plus one entry here.
export const quotationRoutes: RouteObject[] = [
  { path: "quotations", element: <QuotationListPage /> },
  { path: "quotations/:quotationId", element: <QuotationDetailPage /> },
];
