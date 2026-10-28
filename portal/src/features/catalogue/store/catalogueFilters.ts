import { create } from "zustand";

import type { ProductState } from "../model/types";

// Client state only: the product list's search box and filters, kept while moving between
// the list and a product (not stored in the browser).
interface CatalogueFilters {
  text: string;
  categoryId: string; // "" = all categories
  state: ProductState;
  setText: (text: string) => void;
  setCategoryId: (categoryId: string) => void;
  setState: (state: ProductState) => void;
}

export const useCatalogueFilters = create<CatalogueFilters>()((set) => ({
  text: "",
  categoryId: "",
  state: "active",
  setText: (text) => set({ text }),
  setCategoryId: (categoryId) => set({ categoryId }),
  setState: (state) => set({ state }),
}));
