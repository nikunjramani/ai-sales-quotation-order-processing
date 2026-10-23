import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type {
  DeliveryOverview,
  QuotationDetail,
  QuotationStatus,
} from "@/features/quotations/model/types";
import { DocumentPanel } from "@/features/quotations/ui/components/DocumentPanel";

import { jsonResponse, renderWithProviders } from "../../../../support/renderWithProviders";

function detail(status: QuotationStatus): QuotationDetail {
  return {
    summary: {
      quotation_id: "q1",
      enquiry_id: "e1",
      number: "Q-1A2B3C4D",
      status,
      current_version: 2,
      customer_reference: "PO-7",
      currency: "INR",
      total: "10450.38",
      updated_at: "2026-10-23T10:00:00Z",
    },
    enquiry_text: "2 fans",
    pricing_issues: [],
    versions: [
      {
        version: 2,
        content: {
          currency: "INR",
          lines: [],
          subtotal: "8856.25",
          tax: "1594.13",
          total: "10450.38",
          stock_review_required: false,
          calculated_at: "2026-10-23T10:00:00Z",
          policy: { tax_rate: "0.18", rounding: "half_up", minor_units: 2, version: 1 },
        },
        content_sha256: "c".repeat(64),
        created_by: "system:quotation-workflow",
        reason: null,
        created_at: "2026-10-23T10:00:00Z",
      },
    ],
    tasks: [],
    decisions: [],
    pending_task: null,
    can_decide: false,
    can_revise: false,
  };
}

const DELIVERED: DeliveryOverview = {
  document: {
    version: 2,
    sha256: "abcdef0123456789".repeat(4),
    size_bytes: 4608,
    renderer: "quotation-pdf-v1",
    created_at: "2026-10-23T10:05:00Z",
  },
  deliveries: [
    {
      delivery_id: "d1",
      version: 2,
      channel: "api",
      recipient: "api-key:1",
      status: "available",
      provider_reference: null,
      last_error: null,
      created_at: "2026-10-23T10:05:00Z",
      updated_at: "2026-10-23T10:05:00Z",
      delivered_at: "2026-10-23T10:05:00Z",
      first_downloaded_at: null,
    },
  ],
};

describe("DocumentPanel", () => {
  it("offers only a marked preview before approval and asks for no delivery data", () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<DocumentPanel detail={detail("pending_approval")} />);
    const preview = screen.getByRole("link", { name: "Preview PDF of version 2" });
    expect(preview.getAttribute("href")).toBe(
      "/api/v1/tenants/t1/quotations/q1/versions/2/preview.pdf",
    );
    expect(screen.queryByText("Download approved PDF")).toBeNull();
    expect(fetch).not.toHaveBeenCalled();
  });

  it("shows the approved PDF and where it was delivered", async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(200, DELIVERED));
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<DocumentPanel detail={detail("approved")} />);

    const download = await screen.findByRole("link", { name: "Download approved PDF" });
    expect(download.getAttribute("href")).toBe("/api/v1/tenants/t1/quotations/q1/document.pdf");
    expect(screen.getByText(/4\.5 KB · SHA-256 abcdef012345/)).toBeTruthy();
    expect(screen.getByText("Available to the customer")).toBeTruthy();
    expect(screen.getByText("API client")).toBeTruthy();
    expect(fetch.mock.calls[0]?.[0]).toBe("/api/v1/tenants/t1/quotations/q1/delivery");
  });

  it("shows why a delivery failed", async () => {
    const failed: DeliveryOverview = {
      document: null,
      deliveries: [
        {
          ...DELIVERED.deliveries[0]!,
          status: "failed",
          last_error: "business name contains characters the PDF fonts cannot show",
          delivered_at: null,
        },
      ],
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, failed)));
    renderWithProviders(<DocumentPanel detail={detail("approved")} />);

    expect((await screen.findByRole("alert")).textContent).toContain("cannot show");
    expect(screen.getByText("Failed")).toBeTruthy();
    expect(screen.getByText("The approved PDF is being prepared…")).toBeTruthy();
  });
});
