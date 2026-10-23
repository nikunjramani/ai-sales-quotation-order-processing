import { describe, expect, it } from "vitest";

import {
  CUSTOMER_STATUS,
  OUTCOME_LABEL,
  withdrawalProblem,
} from "@/features/quotations/services/customerService";
import { filterById } from "@/features/quotations/services/quotationService";

describe("customer service", () => {
  it("requires a reason to withdraw", () => {
    expect(withdrawalProblem("   ")).toContain("reason");
    expect(withdrawalProblem("x".repeat(1001))).toContain("1000");
    expect(withdrawalProblem("Wrong product")).toBeNull();
  });

  it("labels every customer status and outcome", () => {
    expect(CUSTOMER_STATUS.open.label).toBe("Waiting for the customer");
    expect(CUSTOMER_STATUS.accepted.tone).toBe("good");
    expect(OUTCOME_LABEL.refused_changed).toContain("prices changed");
  });

  it("offers list filters for the customer's answers", () => {
    expect(filterById("accepted").statuses).toEqual(["accepted"]);
    expect(filterById("closed").statuses).toEqual(["declined", "expired", "withdrawn"]);
  });
});
