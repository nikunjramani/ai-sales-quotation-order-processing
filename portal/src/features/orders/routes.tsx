import type { RouteObject } from "react-router";

import { OrderDetailPage } from "./ui/pages/OrderDetailPage";
import { OrderListPage } from "./ui/pages/OrderListPage";

export const orderRoutes: RouteObject[] = [
  { path: "orders", element: <OrderListPage /> },
  { path: "orders/:orderId", element: <OrderDetailPage /> },
];
