import { describe, expect, it } from "vitest";

import {
  passwordHints,
  PROBLEM_TEXT,
  problemsFrom,
} from "@/features/account/services/passwordRules";

describe("passwordRules", () => {
  it("hints the same length and email rules as the server", () => {
    expect(passwordHints("a long passphrase", "ana@shop.example")).toEqual([]);
    expect(passwordHints("short", "ana@shop.example")).toEqual(["too_short"]);
    expect(passwordHints("x".repeat(129), "ana@shop.example")).toEqual(["too_long"]);
    expect(passwordHints("my Ana.lopez words", "ana.lopez@shop.example")).toEqual([
      "contains_email",
    ]);
    // A one- or two-letter email name is not checked (it would refuse almost everything).
    expect(passwordHints("a long passphrase", "al@shop.example")).toEqual([]);
  });

  it("turns the server's refusal into sentences", () => {
    const body = { detail: { message: "x", problems: ["too_common", "too_short"] } };
    expect(problemsFrom(body)).toEqual([PROBLEM_TEXT.too_common, PROBLEM_TEXT.too_short]);
    expect(problemsFrom({ detail: "Not permitted" })).toEqual([]);
  });
});
