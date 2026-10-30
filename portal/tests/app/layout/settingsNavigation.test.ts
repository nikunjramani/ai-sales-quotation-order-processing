import { describe, expect, it } from "vitest";

import { visibleSettings } from "@/app/layout/settingsNavigation";
import type { Permission } from "@/features/auth";

describe("visibleSettings", () => {
  it("lists every section for an administrator, Integrations included", () => {
    expect(visibleSettings(() => true).map((section) => section.label)).toEqual([
      "Business",
      "Pricing",
      "People",
      "Integrations",
      "API keys",
    ]);
  });

  it("shows only the sections a role may open", () => {
    const can = (permission: Permission) => permission === "members:manage";
    expect(visibleSettings(can).map((section) => section.path)).toEqual(["members"]);
  });
});
