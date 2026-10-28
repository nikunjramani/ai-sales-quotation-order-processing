import { describe, expect, it } from "vitest";

import type { Product } from "@/features/catalogue/model/types";
import {
  checkProductForm,
  conflictCodeFrom,
  emptyProductForm,
  fieldProblemFrom,
  formFromProduct,
  hasChanges,
  thousandths,
  toCreatePayload,
  toPatchPayload,
} from "@/features/catalogue/services/productFormService";

const UNITS = ["box", "each", "kg", "metre"];

const PRODUCT: Product = {
  product_id: "p1",
  sku: "IND-BOLT-M8",
  name: "M8 hex bolt",
  unit: "each",
  category: null,
  archived_at: null,
  row_version: 3,
  current_price: null,
  stock: null,
  description: null,
  minimum_quantity: "100",
  quantity_step: "50",
  scheduled_price: null,
  created_at: "2026-10-28T00:00:00Z",
  updated_at: "2026-10-28T00:00:00Z",
};

describe("product form checks", () => {
  it("starts with each and quantities of 1", () => {
    expect(emptyProductForm(UNITS)).toMatchObject({ unit: "each", minimum_quantity: "1", quantity_step: "1" });
  });

  it("checks the SKU only for new products", () => {
    const form = { ...emptyProductForm(UNITS), sku: "bad sku", name: "Bolt" };
    expect(checkProductForm(form, UNITS, true)?.field).toBe("sku");
    expect(checkProductForm(form, UNITS, false)).toBeNull();
  });

  it.each([
    [{ name: " " }, "name"],
    [{ unit: "litre" }, "unit"],
    [{ minimum_quantity: "0" }, "minimum_quantity"],
    [{ quantity_step: "0.0001" }, "quantity_step"],
    [{ minimum_quantity: "75", quantity_step: "50" }, "minimum_quantity"],
  ])("refuses %o", (change, field) => {
    const form = { ...emptyProductForm(UNITS), sku: "X-1", name: "Bolt", ...change };
    expect(checkProductForm(form, UNITS, true)?.field).toBe(field);
  });

  it("checks multiples without floating-point errors", () => {
    expect(thousandths("0.3")).toBe(300n);
    const form = { ...emptyProductForm(UNITS), sku: "C", name: "Cable", minimum_quantity: "0.3", quantity_step: "0.1" };
    expect(checkProductForm(form, UNITS, true)).toBeNull(); // 0.3 / 0.1 in floats is 2.9999…
  });
});

describe("payloads", () => {
  it("sends only changed fields with the starting version", () => {
    const form = { ...formFromProduct(PRODUCT), name: "M8 bolt, zinc", description: "  " };
    const patch = toPatchPayload(form, PRODUCT);
    expect(patch).toEqual({ expected_version: 3, name: "M8 bolt, zinc" });
    expect(hasChanges(toPatchPayload(formFromProduct(PRODUCT), PRODUCT))).toBe(false);
  });

  it("turns empty optional fields into null", () => {
    const payload = toCreatePayload({ ...emptyProductForm(UNITS), sku: " X ", name: " Y " });
    expect(payload).toMatchObject({ sku: "X", name: "Y", description: null, category_id: null });
  });

  it("reads the server's field problem and conflict code", () => {
    expect(fieldProblemFrom({ detail: { field: "unit", message: "No" } })).toEqual({ field: "unit", message: "No" });
    expect(fieldProblemFrom({ detail: "text" })).toBeNull();
    expect(conflictCodeFrom({ detail: { code: "sku_taken", message: "Taken" } })).toBe("sku_taken");
  });
});
