import { describe, expect, it } from "vitest";

import {
  ageText,
  checkPriceText,
  checkStockText,
  midnightIn,
  pricePayload,
  priceLine,
  stockLine,
  stockPayload,
  tomorrow,
} from "@/features/catalogue/services/priceService";

describe("prices", () => {
  it("shows amounts exactly as the server sent them", () => {
    expect(priceLine({ unit_price: "4250.00", currency: "INR", unit: "each" })).toBe("4250.00 INR per each");
  });

  it.each(["0", "0.00", "-1", "1.1234567", "abc", ""])("refuses %s", (text) => {
    expect(checkPriceText(text)).not.toBeNull();
  });

  it("accepts up to 6 decimals", () => {
    expect(checkPriceText("2.375")).toBeNull();
    expect(checkPriceText("0.000001")).toBeNull();
  });

  it("starts a scheduled price at midnight in the business's time zone", () => {
    expect(midnightIn("2026-11-01", "Asia/Kolkata")).toBe("2026-10-31T18:30:00.000Z");
    expect(midnightIn("2026-11-01", "Europe/Berlin")).toBe("2026-10-31T23:00:00.000Z"); // after DST
    expect(midnightIn("2026-11-01", null)).toBe("2026-11-01T00:00:00.000Z");
  });

  it("builds the payload: now, or a date", () => {
    expect(pricePayload(" 10 ", null, null, " ", "c1")).toEqual({
      unit_price: "10",
      effective_from: null,
      note: null,
      command_id: "c1",
    });
    expect(pricePayload("10", "2026-11-01", "Asia/Kolkata", "x", "c2").effective_from).toBe(
      "2026-10-31T18:30:00.000Z",
    );
  });

  it("tomorrow is on the local calendar", () => {
    expect(tomorrow(new Date(2026, 11, 31, 23, 30))).toBe("2027-01-01");
  });
});

describe("stock", () => {
  it("allows not tracked and refuses negatives", () => {
    expect(checkStockText("", true)).toBeNull();
    expect(checkStockText("-1", false)).not.toBeNull();
    expect(checkStockText("12.5", false)).toBeNull();
    expect(stockPayload("5", true, null, "", "c").quantity).toBeNull();
    expect(stockLine({ quantity: null, unit: "metre" })).toBe("Not tracked");
    expect(stockLine({ quantity: "12.5", unit: "metre" })).toBe("12.5 metre");
  });

  it("describes the stock age limit", () => {
    expect(ageText(604800)).toBe("7 day(s)");
    expect(ageText(300)).toBe("5 minute(s)");
    expect(ageText(null)).toBe("not set");
  });
});
