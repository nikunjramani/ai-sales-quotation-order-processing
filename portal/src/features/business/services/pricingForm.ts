// Service: converting what managers type ("18" %) to what the server stores ("0.18") with
// plain string arithmetic. Floating point would turn 0.07 into 0.07000000000000001, and
// money rules must never round by accident.

/** "18" or "18.5" (%) -> "0.18" / "0.185". Null when the text is not a percentage we accept
 * (0 to below 100, at most 4 decimals, so the fraction has at most 6, like the server). */
export function percentToFraction(text: string): string | null {
  const value = text.trim();
  const match = /^(\d{1,2})(?:\.(\d{1,4}))?$/.exec(value);
  if (!match) return null;
  const whole = match[1]!.padStart(2, "0");
  const decimals = `${whole}${match[2] ?? ""}`.replace(/0+$/, "");
  return decimals === "" ? "0" : `0.${decimals}`;
}

/** "0.18" -> "18"; "0.185" -> "18.5"; null stays empty. */
export function fractionToPercent(fraction: string | null): string {
  if (fraction === null) return "";
  const match = /^0(?:\.(\d{1,6}))?$/.exec(fraction.trim());
  if (!match) return "";
  const digits = (match[1] ?? "").padEnd(2, "0");
  const whole = String(Number(digits.slice(0, 2)));
  const rest = digits.slice(2).replace(/0+$/, "");
  return rest ? `${whole}.${rest}` : whole;
}

/** Suggested decimal places for a currency (ISO 4217, via the browser), e.g. INR 2, JPY 0.
 * A suggestion only: the manager confirms every pricing value (Q14). */
export function suggestedMinorUnits(currency: string): number | null {
  if (!/^[A-Z]{3}$/.test(currency)) return null;
  try {
    const format = new Intl.NumberFormat("en", { style: "currency", currency });
    return format.resolvedOptions().maximumFractionDigits ?? null;
  } catch {
    return null;
  }
}

/** The demo values, shown as suggestions on an empty pricing screen (Q14). */
export const SUGGESTED = {
  rounding_mode: "half_up" as const,
  max_price_age_minutes: 15,
  // Typed stock counts age for days, not minutes (phase 3, Q10): 7 days.
  max_stock_age_minutes: 7 * 24 * 60,
};
