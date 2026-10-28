import { describe, expect, it } from "vitest";

import { roleText, tokenFromSearch } from "@/features/account/services/links";

describe("links", () => {
  it("reads only token-shaped values from an email link", () => {
    const token = "ZO9jh--ZeT9NVYflaXDdAIhotSsPGydbQi0pJ8DyTyI";
    expect(tokenFromSearch(`?token=${token}`)).toBe(token);
    expect(tokenFromSearch("")).toBeNull();
    expect(tokenFromSearch("?token=short")).toBeNull();
    expect(tokenFromSearch("?token=<script>alert(1)</script>xxxxxxxxxxxx")).toBeNull();
  });

  it("names roles in plain words", () => {
    expect(roleText(["approver", "sales_operator"])).toBe("Approver, Sales operator");
  });
});
