// Service: the product form's checks and payloads. They mirror the server's rules so people
// see problems before saving; the server checks everything again (phase 3, Q1-Q4, Q16).

import type { FieldProblem, Product, ProductForm, ProductPatch, ProductPayload } from "../model/types";

export const SKU_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._/-]{0,63}$/;
const QUANTITY_PATTERN = /^\d{1,9}(\.\d{1,3})?$/;

export function emptyProductForm(units: readonly string[]): ProductForm {
  return {
    sku: "",
    name: "",
    unit: units.includes("each") ? "each" : (units[0] ?? ""),
    description: "",
    category_id: "",
    minimum_quantity: "1",
    quantity_step: "1",
  };
}

export function formFromProduct(product: Product): ProductForm {
  return {
    sku: product.sku,
    name: product.name,
    unit: product.unit,
    description: product.description ?? "",
    category_id: product.category?.category_id ?? "",
    minimum_quantity: product.minimum_quantity,
    quantity_step: product.quantity_step,
  };
}

/** "1.5" -> 1500n (thousandths), so multiples are checked without floating-point errors. */
export function thousandths(value: string): bigint {
  const [whole = "0", fraction = ""] = value.split(".");
  return BigInt(whole) * 1000n + BigInt(fraction.padEnd(3, "0"));
}

/** The first problem in the form, or null. `isNew` also checks the SKU (it never changes). */
export function checkProductForm(
  form: ProductForm,
  units: readonly string[],
  isNew: boolean,
): FieldProblem | null {
  if (isNew && !SKU_PATTERN.test(form.sku.trim())) {
    return {
      field: "sku",
      message: "SKU: 1-64 letters, digits or - _ . /, starting with a letter or digit.",
    };
  }
  if (!form.name.trim()) return { field: "name", message: "Enter a name." };
  if (form.name.trim().length > 200) return { field: "name", message: "Name: at most 200 characters." };
  if (!units.includes(form.unit)) {
    return { field: "unit", message: `Unit: one of ${units.join(", ")}.` };
  }
  if (form.description.length > 2000) {
    return { field: "description", message: "Description: at most 2000 characters." };
  }
  for (const [field, label] of [
    ["minimum_quantity", "Minimum quantity"],
    ["quantity_step", "Quantity step"],
  ] as const) {
    const value = form[field].trim();
    if (!QUANTITY_PATTERN.test(value) || thousandths(value) === 0n) {
      return { field, message: `${label}: a number above 0 with at most 3 decimals.` };
    }
  }
  if (thousandths(form.minimum_quantity.trim()) % thousandths(form.quantity_step.trim()) !== 0n) {
    return {
      field: "minimum_quantity",
      message: "Minimum quantity must be a multiple of the step, so it can be ordered.",
    };
  }
  return null;
}

export function toCreatePayload(form: ProductForm): ProductPayload {
  return {
    sku: form.sku.trim(),
    name: form.name.trim(),
    unit: form.unit,
    description: form.description.trim() || null,
    category_id: form.category_id || null,
    minimum_quantity: form.minimum_quantity.trim(),
    quantity_step: form.quantity_step.trim(),
  };
}

/** Only the fields that changed, plus the version the person started from. */
export function toPatchPayload(form: ProductForm, product: Product): ProductPatch {
  const next = toCreatePayload(form);
  const before = toCreatePayload(formFromProduct(product));
  const patch: ProductPatch = { expected_version: product.row_version };
  for (const key of [
    "name",
    "unit",
    "description",
    "category_id",
    "minimum_quantity",
    "quantity_step",
  ] as const) {
    if (next[key] !== before[key]) (patch as Record<string, unknown>)[key] = next[key];
  }
  return patch;
}

export function hasChanges(patch: ProductPatch): boolean {
  return Object.keys(patch).length > 1;
}

/** The server's {field, message} detail on a 422, if any. */
export function fieldProblemFrom(detail: unknown): FieldProblem | null {
  const inner = innerDetail(detail);
  if (inner && typeof inner === "object" && "field" in inner && "message" in inner) {
    return { field: String(inner.field), message: String(inner.message) };
  }
  return null;
}

/** The server's conflict code on a 409 (e.g. "version_conflict", "sku_taken"), if any. */
export function conflictCodeFrom(detail: unknown): string | null {
  const inner = innerDetail(detail);
  if (inner && typeof inner === "object" && "code" in inner) return String(inner.code);
  return null;
}

function innerDetail(detail: unknown): unknown {
  return detail && typeof detail === "object" && "detail" in detail
    ? (detail as { detail: unknown }).detail
    : null;
}
