import type { RouteObject } from "react-router";

import { CategoriesPage } from "./ui/pages/CategoriesPage";
import { ProductListPage } from "./ui/pages/ProductListPage";
import { ProductPage } from "./ui/pages/ProductPage";

export const catalogueRoutes: RouteObject[] = [
  { path: "catalogue", element: <ProductListPage /> },
  { path: "catalogue/new", element: <ProductPage /> },
  { path: "catalogue/categories", element: <CategoriesPage /> },
  { path: "catalogue/:productId", element: <ProductPage /> },
];
