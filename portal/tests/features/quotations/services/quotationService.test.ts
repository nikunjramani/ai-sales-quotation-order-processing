import { describe, expect, it } from "vitest";

import type { QuotationDetail } from "@/features/quotations/model/types";
import {
  cleanLines,
  decisionProblem,
  filterById,
  initialRevisionLines,
  pricingIssuesFrom,
  revisionProblem,
} from "@/features/quotations/services/quotationService";

function detail(lines: { sku: string; quantity: string; unit: string }[]): QuotationDetail {
  return {
    summary: {
      quotation_id: "q1",
      enquiry_id: "e1",
      number: "Q-1",
      status: "revision_requested",
      current_version: lines.length ? 1 : null,
      customer_reference: null,
      currency: "INR",
      total: null,
      updated_at: "2026-10-23T10:00:00Z",
    },
    enquiry_text: "",
    pricing_issues: [],
    versions: lines.length
      ? [
          {
            version: 1,
            content_sha256: "a".repeat(64),
            created_by: "system",
            reason: null,
            created_at: "2026-10-23T10:00:00Z",
            content: {
              currency: "INR",
              subtotal: "0",
              tax: "0",
              total: "0",
              stock_review_required: false,
              calculated_at: "2026-10-23T10:00:00Z",
              policy: { tax_rate: "0.18", rounding: "half_up", minor_units: 2, version: 1 },
              lines: lines.map((line, index) => ({
                ...line,
                line_index: index,
                description: "",
                unit_price: "1",
                line_total: "1",
                price_list_id: "P",
                price_list_version: "1",
                stock_status: "available",
                stock_available: null,
                stock_note: "",
              })),
            },
          },
        ]
      : [],
    tasks: [],
    decisions: [],
    pending_task: null,
    can_decide: false,
    can_revise: true,
  };
}

describe("quotation service", () => {
  it("falls back to the first filter for unknown ids", () => {
    expect(filterById("revision").statuses).toEqual(["revision_requested", "pricing_failed"]);
    expect(filterById("nonsense").id).toBe("waiting");
    expect(filterById(null).id).toBe("waiting");
  });

  it("needs a reason to reject or request a revision, not to approve", () => {
    expect(decisionProblem("approve", "")).toBeNull();
    expect(decisionProblem("reject", "  ")).toMatch(/reason/);
    expect(decisionProblem("request_revision", "3 fans")).toBeNull();
    expect(decisionProblem("reject", "x".repeat(1001))).toMatch(/1000/);
  });

  it("starts a revision from the current lines, or one empty line when unpriced", () => {
    expect(initialRevisionLines(detail([{ sku: "IND-FAN-450", quantity: "2", unit: "each" }]))).toEqual([
      { sku: "IND-FAN-450", quantity: "2", unit: "each" },
    ]);
    expect(initialRevisionLines(detail([]))).toEqual([{ sku: "", quantity: "1", unit: "each" }]);
  });

  it("drops blank lines, trims text and keeps quantities as exact strings", () => {
    const lines = [
      { sku: " IND-FAN-450 ", quantity: " 2.50 ", unit: " each " },
      { sku: "  ", quantity: "1", unit: "each" },
    ];
    expect(cleanLines(lines)).toEqual([{ sku: "IND-FAN-450", quantity: "2.50", unit: "each" }]);
    expect(revisionProblem([lines[1]!], "why")).toMatch(/line/);
    expect(revisionProblem(lines, " ")).toMatch(/changed/);
    expect(revisionProblem(lines, "3 fans")).toBeNull();
  });

  it("reads pricing issues from a 422 body and ignores anything else", () => {
    const issue = { line_index: 0, sku: "IND-PUMP-2HP", code: "price_missing", message: "No price" };
    expect(pricingIssuesFrom({ detail: "x", issues: [issue] })).toEqual([issue]);
    expect(pricingIssuesFrom({ detail: "x" })).toEqual([]);
    expect(pricingIssuesFrom(null)).toEqual([]);
  });
});
