// Service: pure enquiry list rules.

export const ENQUIRY_FILTERS = [
  { id: "attention", label: "Needs a person", statuses: ["needs_review", "needs_clarification"] },
  { id: "all", label: "All", statuses: [] },
] as const satisfies readonly { id: string; label: string; statuses: readonly string[] }[];

export function enquiryFilterById(id: string | null): (typeof ENQUIRY_FILTERS)[number] {
  return ENQUIRY_FILTERS.find((filter) => filter.id === id) ?? ENQUIRY_FILTERS[0];
}
