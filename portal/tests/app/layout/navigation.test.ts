import { describe, expect, it } from "vitest";

import { visibleNavigation } from "@/app/layout/navigation";
import type { Permission } from "@/features/auth";

describe("visibleNavigation", () => {
  it("shows only what the role can open, in plain words", () => {
    const can = (permission: Permission) => permission === "quotations:view";
    expect(visibleNavigation(can, false).map((item) => item.label)).toEqual([
      "Home",
      "Quotes",
      "Customer requests",
    ]);
  });

  it("puts Get started first while the business is being set up", () => {
    const items = visibleNavigation(() => true, true);
    expect(items[0]?.label).toBe("Get started");
    expect(items.map((item) => item.label)).toContain("Settings");
  });
});
