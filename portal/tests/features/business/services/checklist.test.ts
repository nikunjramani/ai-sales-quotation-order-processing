import { describe, expect, it } from "vitest";

import { missingFrom, remainingRequired } from "@/features/business/services/checklist";

describe("checklist", () => {
  it("counts required steps and reads the missing ones from a refusal", () => {
    expect(
      remainingRequired([
        { key: "pricing", done: false, required: true },
        { key: "product_source", done: false, required: false },
        { key: "approver", done: true, required: true },
      ]),
    ).toBe(1);
    const refusal = { detail: { message: "Finish the setup first", missing: ["test_enquiry"] } };
    expect(missingFrom(refusal)).toEqual(["test_enquiry"]);
    expect(missingFrom({ detail: "x" })).toEqual([]);
  });
});
