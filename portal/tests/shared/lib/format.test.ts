import { describe, expect, it } from "vitest";

import { money, percent } from "@/shared/lib/format";

describe("percent", () => {
  it.each([
    ["0.18", "18"],
    ["0.180000", "18"],
    ["0.185", "18.5"],
    ["0.05", "5"],
    ["0", "0"],
    ["0.1", "10"],
  ])("%s -> %s", (rate, expected) => {
    expect(percent(rate)).toBe(expected);
  });
});

describe("money", () => {
  it("shows the exact server amount, or a dash when there is none", () => {
    expect(money("10450.38", "INR")).toBe("10450.38 INR");
    expect(money(null, null)).toBe("—");
  });
});
