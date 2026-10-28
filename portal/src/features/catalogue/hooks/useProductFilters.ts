import { useCatalogueFilters } from "../store/catalogueFilters";

/** The product list's search and filters (client state, kept while browsing products). */
export function useProductFilters() {
  return useCatalogueFilters();
}
