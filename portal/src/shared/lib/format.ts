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

/** 4608 -> "4.5 KB". For file sizes only (display, no maths on money). */
export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) return `${kilobytes.toFixed(1)} KB`;
  return `${(kilobytes / 1024).toFixed(1)} MB`;
}

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}
