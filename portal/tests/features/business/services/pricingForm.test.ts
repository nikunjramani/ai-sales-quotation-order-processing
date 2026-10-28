import { describe, expect, it } from "vitest";

import {
  fractionToPercent,
  percentToFraction,
  suggestedMinorUnits,
} from "@/features/business/services/pricingForm";

describe("pricingForm", () => {
  it("converts percentages exactly, without floating point", () => {
    expect(percentToFraction("18")).toBe("0.18");
    expect(percentToFraction("7")).toBe("0.07");
    expect(percentToFraction("10")).toBe("0.1");
    expect(percentToFraction("18.5")).toBe("0.185");
    expect(percentToFraction("0")).toBe("0");
    expect(percentToFraction("99.9999")).toBe("0.999999");
    expect(percentToFraction(" 5 ")).toBe("0.05");
  });

  it("refuses what the server would refuse", () => {
    for (const text of ["", "100", "18.00001", "-1", "1e1", "abc", "18,5"]) {
      expect(percentToFraction(text), text).toBeNull();
    }
  });

  it("shows stored fractions as percentages", () => {
    expect(fractionToPercent("0.18")).toBe("18");
    expect(fractionToPercent("0.185")).toBe("18.5");
    expect(fractionToPercent("0.07")).toBe("7");
    expect(fractionToPercent("0.1")).toBe("10");
    expect(fractionToPercent("0")).toBe("0");
    expect(fractionToPercent(null)).toBe("");
  });

  it("suggests decimal places from the currency", () => {
    expect(suggestedMinorUnits("INR")).toBe(2);
    expect(suggestedMinorUnits("JPY")).toBe(0);
    expect(suggestedMinorUnits("inr")).toBeNull();
  });
});
