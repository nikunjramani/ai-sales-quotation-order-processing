/**
 * "0.18" -> "18", "0.185000" -> "18.5". Moves the decimal point on the string, because
 * floating-point maths would show 0.18 * 100 as 18.000000000000004.
 */
export function percent(rate: string): string {
  const [whole = "0", fraction = ""] = rate.split(".");
  const digits = fraction.padEnd(2, "0");
  const integer = `${whole}${digits.slice(0, 2)}`.replace(/^0+(?=\d)/, "");
  const rest = digits.slice(2).replace(/0+$/, "");
  return rest ? `${integer}.${rest}` : integer;
}

/** Amounts are shown exactly as the server calculated them; the portal never does money maths. */
export function money(amount: string | null, currency: string | null): string {
  return amount === null ? "—" : `${amount} ${currency ?? ""}`.trim();
}

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}
