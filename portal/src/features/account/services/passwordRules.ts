// Service: the password rules as hints for the form (user answer Q1: 12 to 128 characters, no
// "must contain a digit" rules). The server checks them again, plus the common-password list.

import type { PasswordProblem } from "../model/types";

export const MIN_PASSWORD = 12;
export const MAX_PASSWORD = 128;

export const PROBLEM_TEXT: Record<PasswordProblem, string> = {
  too_short: `Use at least ${MIN_PASSWORD} characters; a few words in a row work well.`,
  too_long: `Use at most ${MAX_PASSWORD} characters.`,
  too_common: "This password is too common; choose another.",
  contains_email: "Do not use your email name in the password.",
};

/** Problems the form can see before sending (length and the email name). */
export function passwordHints(password: string, email: string): PasswordProblem[] {
  const problems: PasswordProblem[] = [];
  if (password.length < MIN_PASSWORD) problems.push("too_short");
  if (password.length > MAX_PASSWORD) problems.push("too_long");
  const name = email.split("@")[0]?.toLowerCase() ?? "";
  if (name.length >= 3 && password.toLowerCase().includes(name)) problems.push("contains_email");
  return problems;
}

/** The server's 422 detail for a refused password, as readable sentences. */
export function problemsFrom(detail: unknown): string[] {
  if (detail && typeof detail === "object" && "detail" in detail) {
    const inner = (detail as { detail: unknown }).detail;
    if (inner && typeof inner === "object" && "problems" in inner) {
      const problems = (inner as { problems: unknown }).problems;
      if (Array.isArray(problems)) {
        return problems.map((item) => PROBLEM_TEXT[item as PasswordProblem] ?? String(item));
      }
    }
  }
  return [];
}
