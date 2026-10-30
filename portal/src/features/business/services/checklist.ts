// Service: how each setup step is shown and where it is done. The server computes "done"
// from real data every time; the portal never decides it.

import type { SetupItem, SetupItemKey } from "../model/types";

export const SETUP_STEPS: Record<SetupItemKey, { label: string; hint: string; link: string | null }> = {
  business_details: {
    label: "Business details",
    hint: "Name, country and time zone.",
    link: "/settings/business",
  },
  pdf_details: {
    label: "Details on your quotations",
    hint: "Legal name and address printed on every quotation PDF.",
    link: "/settings/business",
  },
  pricing: {
    label: "Pricing",
    hint: "Currency, tax rate, rounding and how fresh prices must be.",
    link: "/settings/pricing",
  },
  approver: {
    label: "An approver",
    hint: "Someone who approves quotations before customers get them.",
    link: "/settings/members",
  },
  product_source: {
    label: "Products",
    hint: "At least one product with a price, so enquiries can be quoted. Not needed to go live.",
    link: "/catalogue",
  },
  customer_channel: {
    label: "A way for customers to reach you",
    hint: "Website chat, Telegram or an API key for your own system.",
    link: "/settings/integrations",
  },
  test_enquiry: {
    label: "A test enquiry",
    hint: "Send one enquiry through each customer tool to check it works.",
    link: "/settings/api-keys",
  },
};

export function remainingRequired(items: SetupItem[]): number {
  return items.filter((item) => item.required && !item.done).length;
}

/** The server's 409 detail when going live failed: the steps still missing. */
export function missingFrom(detail: unknown): SetupItemKey[] {
  if (detail && typeof detail === "object" && "detail" in detail) {
    const inner = (detail as { detail: unknown }).detail;
    if (inner && typeof inner === "object" && "missing" in inner) {
      const missing = (inner as { missing: unknown }).missing;
      if (Array.isArray(missing)) return missing as SetupItemKey[];
    }
  }
  return [];
}
