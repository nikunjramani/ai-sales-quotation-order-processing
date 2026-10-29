// The visitor's chat session token, remembered per chat in this browser. Storage can be
// blocked (private mode, strict settings): then the session lasts for this page only.

const memory = new Map<string, string>();

function key(handle: string): string {
  return `qa_chat_${handle}`;
}

export function loadToken(handle: string): string | null {
  try {
    return window.localStorage.getItem(key(handle)) ?? memory.get(handle) ?? null;
  } catch {
    return memory.get(handle) ?? null;
  }
}

export function saveToken(handle: string, token: string | null): void {
  if (token === null) memory.delete(handle);
  else memory.set(handle, token);
  try {
    if (token === null) window.localStorage.removeItem(key(handle));
    else window.localStorage.setItem(key(handle), token);
  } catch {
    // storage blocked: the in-memory copy is enough for this page
  }
}

/** A unique key per sent message, so a retried send is stored once. */
export function idempotencyKey(): string {
  const random = crypto.getRandomValues(new Uint8Array(16));
  return `w-${Array.from(random, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}
