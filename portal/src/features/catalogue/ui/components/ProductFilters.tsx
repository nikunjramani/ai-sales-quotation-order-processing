import type { Category, ProductState } from "../../model/types";
import { FilterTabs } from "@/shared/ui/FilterTabs";

const STATES = [
  { id: "active", label: "Active" },
  { id: "archived", label: "Archived" },
  { id: "all", label: "All" },
] as const;

interface Props {
  text: string;
  categoryId: string;
  state: ProductState;
  categories: Category[];
  onText: (text: string) => void;
  onCategory: (categoryId: string) => void;
  onState: (state: ProductState) => void;
}

export function ProductFilters(props: Props) {
  return (
    <div className="card">
      <FilterTabs tabs={STATES} selected={props.state} onSelect={(id) => props.onState(id as ProductState)} />
      <label htmlFor="catalogue-search">Search SKU or name</label>
      <input
        id="catalogue-search"
        type="search"
        maxLength={100}
        value={props.text}
        onChange={(event) => props.onText(event.target.value)}
      />
      <label htmlFor="catalogue-category">Category</label>
      <select id="catalogue-category" value={props.categoryId} onChange={(event) => props.onCategory(event.target.value)}>
        <option value="">All categories</option>
        {props.categories.map((category) => (
          <option key={category.category_id} value={category.category_id}>
            {category.name}
          </option>
        ))}
      </select>
    </div>
  );
}
