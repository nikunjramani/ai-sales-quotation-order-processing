/** A new ID per user action. Retrying the same action reuses it, so the server applies it once. */
export function newCommandId(): string {
  return crypto.randomUUID();
}
