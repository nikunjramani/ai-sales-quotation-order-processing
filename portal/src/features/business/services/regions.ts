// Service: country and time zone helpers from the browser's own data (Intl), so no list has to
// be maintained here. The server validates both again (country pattern, PostgreSQL's zones).

/** "IN" -> "India"; null when it is not a known two-letter region code. */
export function countryName(code: string): string | null {
  if (!/^[A-Z]{2}$/.test(code)) return null;
  try {
    const name = new Intl.DisplayNames(["en"], { type: "region" }).of(code);
    return name && name !== code ? name : null;
  } catch {
    return null;
  }
}

/** The browser's time zone, the pre-filled suggestion (Q15). */
export function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

export function timeZones(): string[] {
  const supported = (Intl as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf;
  return supported ? supported("timeZone") : [browserTimeZone()];
}
