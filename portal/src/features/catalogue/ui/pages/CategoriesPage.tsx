import { useState } from "react";
import { Link } from "react-router";

import { useCanEditCatalogue, useCategories } from "../../hooks/useCatalogue";
import { useCategoryForms } from "../../hooks/useCatalogueForms";
import type { Category } from "../../model/types";
import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

/** Product groups. Customers are told the categories that have products (ADR 0017). */
export function CategoriesPage() {
  const categories = useCategories();
  const canEdit = useCanEditCatalogue();
  const forms = useCategoryForms();
  return (
    <section>
      <p>
        <Link to="/catalogue">← Products</Link>
      </p>
      <h1>Categories</h1>
      <p className="muted small">
        When a customer asks for something you do not sell, the reply lists your categories that
        have active products.
      </p>
      {canEdit && (
        <form className="card" onSubmit={forms.submit}>
          <label htmlFor="category-name">New category</label>
          <input id="category-name" maxLength={100} value={forms.name} onChange={(event) => forms.setName(event.target.value)} />
          <button type="submit" disabled={forms.create.isPending || !forms.name.trim()}>
            Add category
          </button>
        </form>
      )}
      <ErrorMessage message={forms.error.field?.message ?? forms.error.message} />
      <QueryState isLoading={categories.isLoading} error={categories.error} isEmpty={categories.data?.length === 0} emptyText="No categories yet.">
        <ul className="plain">
          {(categories.data ?? []).map((category) => (
            <CategoryRow key={`${category.category_id}-${category.row_version}`} category={category} editable={canEdit} forms={forms} />
          ))}
        </ul>
      </QueryState>
    </section>
  );
}

function CategoryRow({
  category,
  editable,
  forms,
}: {
  category: Category;
  editable: boolean;
  forms: ReturnType<typeof useCategoryForms>;
}) {
  const [name, setName] = useState(category.name);
  const archived = category.archived_at !== null;
  return (
    <li className="card">
      {editable ? (
        <input aria-label={`Name of ${category.name}`} maxLength={100} value={name} onChange={(event) => setName(event.target.value)} />
      ) : (
        <strong>{category.name}</strong>
      )}{" "}
      <span className="muted small">{category.active_products} active product(s)</span>
      {archived && <span className="badge"> Archived</span>}
      {editable && (
        <div className="actions">
          <button
            className="secondary"
            disabled={!name.trim() || name.trim() === category.name}
            onClick={() =>
              forms.update.mutate({ categoryId: category.category_id, name: name.trim(), version: category.row_version })
            }
          >
            Rename
          </button>
          <button
            className="secondary"
            onClick={() =>
              forms.update.mutate({ categoryId: category.category_id, archived: !archived, version: category.row_version })
            }
          >
            {archived ? "Restore" : "Archive"}
          </button>
        </div>
      )}
    </li>
  );
}
