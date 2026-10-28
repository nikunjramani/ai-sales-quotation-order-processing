import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CatalogueSummary, ProductPage } from "@/features/catalogue/model/types";
import { ProductListPage } from "@/features/catalogue/ui/pages/ProductListPage";

import {
  jsonResponse,
  renderWithProviders,
  testQueryClient,
  TEST_SESSION,
} from "../../../../support/renderWithProviders";

function session(permissions: string[]) {
  return {
    ...TEST_SESSION,
    tenants: [{ ...TEST_SESSION.tenants[0]!, roles: ["sales_operator"], permissions }],
  } as typeof TEST_SESSION;
}

function summary(editable: boolean): CatalogueSummary {
  return {
    source: { provider_key: "x", display_name: editable ? "Our product list" : "Acme ERP", editable },
    active_products: 1,
    priced_products: 0,
    products_without_price: 1,
    stale_stock: 1,
    unknown_stock: 0,
    max_active_products: 10000,
    units: ["box", "each", "kg", "metre"],
    currency: "INR",
    minor_units: 2,
    max_stock_age_seconds: 604800,
    time_zone: "Asia/Kolkata",
  };
}

const PAGE: ProductPage = {
  next_after: null,
  items: [
    {
      product_id: "p1",
      sku: "IND-FAN-450",
      name: "Industrial exhaust fan",
      unit: "each",
      category: null,
      archived_at: null,
      row_version: 1,
      current_price: null,
      stock: {
        stock_id: "s1",
        quantity: "120",
        unit: "each",
        location: "MAIN",
        as_of: "2026-10-01T00:00:00Z",
        source: "manual",
        note: null,
        recorded_at: "2026-10-01T00:00:00Z",
        recorded_by: "sales",
        stale: true,
      },
    },
  ],
};

function serve(editable: boolean) {
  return vi.fn((url: string) =>
    Promise.resolve(
      url.includes("/summary")
        ? jsonResponse(200, summary(editable))
        : url.includes("/categories")
          ? jsonResponse(200, [])
          : jsonResponse(200, PAGE),
    ),
  );
}

describe("ProductListPage", () => {
  it("shows missing prices and old counts, and the add button for editors", async () => {
    vi.stubGlobal("fetch", serve(true));
    renderWithProviders(<ProductListPage />, {
      client: testQueryClient(session(["catalogue:view", "catalogue:manage"])),
    });
    expect(await screen.findByText("IND-FAN-450")).toBeTruthy();
    expect(screen.getByText("No price")).toBeTruthy();
    expect(screen.getByText(/Old count/)).toBeTruthy();
    expect(await screen.findByRole("link", { name: "Add product" })).toBeTruthy();
  });

  it("hides editing for people without catalogue:manage", async () => {
    vi.stubGlobal("fetch", serve(true));
    renderWithProviders(<ProductListPage />, { client: testQueryClient(session(["catalogue:view"])) });
    expect(await screen.findByText("IND-FAN-450")).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Add product" })).toBeNull();
  });

  it("is read-only with a banner when products come from another source", async () => {
    vi.stubGlobal("fetch", serve(false));
    renderWithProviders(<ProductListPage />, {
      client: testQueryClient(session(["catalogue:view", "catalogue:manage"])),
    });
    expect(await screen.findByText(/Products come from Acme ERP/)).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Add product" })).toBeNull();
  });
});
