// The only place the widget talks HTTP: our public chat API (phase 4). No cookies are sent;
// the visitor's session token goes in the Authorization header.

export interface ChatConfig {
  business_name: string;
  greeting: string;
  max_message_chars: number;
  files_per_message: number;
  max_file_bytes: number;
}

export interface ChatAction {
  action: "accept" | "decline";
  label: string;
  ref: string;
}

export interface ChatMessage {
  seq: number;
  direction: "inbound" | "outbound";
  kind: "text" | "questions" | "quotation" | "confirmation" | "notice";
  text: string;
  at: string;
  quotation: { number: string; version: string; document_path: string | null; actions: ChatAction[] } | null;
}

export interface ChatFile {
  filename: string;
  content_type: string;
  content_base64: string;
}

export class ChatError extends Error {
  constructor(
    readonly status: number,
    message: string,
    readonly retryAfterSeconds = 0,
  ) {
    super(message);
  }
}

export function createChatClient(baseUrl: string, handle: string) {
  const root = `${baseUrl}/api/v1/public/chat/${encodeURIComponent(handle)}`;

  async function call<T>(path: string, init: RequestInit, token?: string): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (init.body) headers.set("Content-Type", "application/json");
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${root}${path}`, { ...init, headers, credentials: "omit" });
    if (!response.ok) {
      let message = "Something went wrong; please try again";
      try {
        const data = (await response.json()) as { detail?: unknown };
        if (typeof data.detail === "string") message = data.detail;
      } catch {
        // keep the generic message
      }
      throw new ChatError(response.status, message, Number(response.headers.get("Retry-After") ?? 0));
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    config: () => call<ChatConfig>("/config", {}),
    start: (body: { name: string; email?: string; phone?: string; website: string; form_ms: number }) =>
      call<{ session_token: string }>("/sessions", { method: "POST", body: JSON.stringify(body) }),
    send: (token: string, text: string, files: ChatFile[], key: string) =>
      call<{ duplicate: boolean }>(
        "/messages",
        { method: "POST", body: JSON.stringify({ text, attachments: files }), headers: { "Idempotency-Key": key } },
        token,
      ),
    poll: (token: string, after: number) =>
      call<{ messages: ChatMessage[]; after: number; poll_ms: number }>(`/messages?after=${after}`, {}, token),
    act: (token: string, ref: string, action: "accept" | "decline") =>
      call<{ outcome: string }>(`/actions/${encodeURIComponent(ref)}`, {
        method: "POST",
        body: JSON.stringify({ action }),
      }, token),
    /** The PDF as a Blob (the download needs the token, so it is not a plain link). */
    async document(token: string, path: string): Promise<Blob> {
      const response = await fetch(`${baseUrl}${path}`, {
        headers: { Authorization: `Bearer ${token}` },
        credentials: "omit",
      });
      if (!response.ok) throw new ChatError(response.status, "The document is not available");
      return response.blob();
    },
    end: (token: string) => call<void>("/session/end", { method: "POST" }, token),
  };
}

export type ChatClient = ReturnType<typeof createChatClient>;
