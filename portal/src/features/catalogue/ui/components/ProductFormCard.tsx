import { useCategories } from "../../hooks/useCatalogue";
import { useProductForm } from "../../hooks/useCatalogueForms";
import type { Product, ProductForm } from "../../model/types";
import { ErrorMessage } from "@/shared/ui/QueryState";

interface Props {
  units: readonly string[];
  product: Product | null; // null: a new product
  editable: boolean;
  onSaved: (saved: Product) => void;
}

/** Add or edit a product's details. The SKU is fixed once created (Q2). */
export function ProductFormCard({ units, product, editable, onSaved }: Props) {
  const form = useProductForm(units, product, onSaved);
  const categories = useCategories();
  const field = (name: keyof ProductForm) => ({
    id: `product-${name}`,
    value: form.form[name],
    disabled: !editable,
    "aria-invalid": form.problem?.field === name || undefined,
    onChange: (event: { target: { value: string } }) => form.set(name, event.target.value),
  });
  const choices = (categories.data ?? []).filter(
    (category) => !category.archived_at || category.category_id === form.form.category_id,
  );
  return (
    <form className="card" onSubmit={form.submit}>
      <label htmlFor="product-sku">SKU (product code)</label>
      <input {...field("sku")} disabled={!editable || product !== null} required maxLength={64} />
      {product !== null && <p className="muted small">A SKU never changes; archive the product and add a new one instead.</p>}
      <label htmlFor="product-name">Name (customers see this)</label>
      <input {...field("name")} required maxLength={200} />
      <label htmlFor="product-unit">Unit</label>
      <select {...field("unit")}>
        {units.map((unit) => (
          <option key={unit} value={unit}>
            {unit}
          </option>
        ))}
      </select>
      <label htmlFor="product-category_id">Category</label>
      <select {...field("category_id")}>
        <option value="">No category</option>
        {choices.map((category) => (
          <option key={category.category_id} value={category.category_id}>
            {category.name}
          </option>
        ))}
      </select>
      <label htmlFor="product-minimum_quantity">Minimum order quantity</label>
      <input {...field("minimum_quantity")} inputMode="decimal" />
      <label htmlFor="product-quantity_step">Order in steps of</label>
      <input {...field("quantity_step")} inputMode="decimal" />
      <label htmlFor="product-description">Notes for staff (not shown to customers)</label>
      <textarea {...field("description")} maxLength={2000} rows={3} />
      <ErrorMessage message={form.problem?.message ?? form.error} />
      {editable && (
        <button type="submit" disabled={form.busy || form.unchanged}>
          {product ? "Save changes" : "Add product"}
        </button>
      )}
    </form>
  );
}
