import { describe, expect, it, vi } from "vitest";

import type { ChatClient, ChatMessage } from "@/widget/api/chatClient";
import { loadToken, saveToken } from "@/widget/state/session";
import { mountChat } from "@/widget/ui/chatView";

function fakeClient(messages: ChatMessage[] = []) {
  return {
    config: vi.fn().mockResolvedValue({
      business_name: "Acme",
      greeting: "Hello <b>there</b>",
      max_message_chars: 2000,
      files_per_message: 5,
      max_file_bytes: 5 * 1024 * 1024,
    }),
    start: vi.fn().mockResolvedValue({ session_token: "cs_token" }),
    send: vi.fn().mockResolvedValue({ duplicate: false }),
    poll: vi.fn().mockResolvedValue({ messages, after: messages.length, poll_ms: 3000 }),
    act: vi.fn().mockResolvedValue({ outcome: "accepted" }),
    document: vi.fn(),
    end: vi.fn(),
  } satisfies ChatClient;
}

async function mounted(client: ReturnType<typeof fakeClient>, handle: string) {
  const host = document.createElement("div");
  document.body.append(host);
  await mountChat(host, client, handle, true);
  await new Promise((resolve) => setTimeout(resolve, 0));
  return host.shadowRoot!;
}

describe("website chat widget", () => {
  it("asks for a name and an email or phone before starting", async () => {
    const client = fakeClient();
    const root = await mounted(client, "acme-a");
    expect(root.textContent).toContain("Hello <b>there</b>"); // text, not HTML
    expect(root.querySelector("b")).toBeNull();
    const [name] = Array.from(root.querySelectorAll("input"));
    name!.value = "Asha";
    root.querySelector("form")!.dispatchEvent(new Event("submit", { cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(root.textContent).toContain("Please give an email address or a phone number");
    expect(client.start).not.toHaveBeenCalled();
  });

  it("shows messages as text and quotation buttons from the server", async () => {
    saveToken("acme-b", "cs_token");
    const client = fakeClient([
      {
        seq: 1, direction: "outbound", kind: "quotation",
        text: "Your quotation Q-1 (version 1) is ready <script>x</script>",
        at: "2026-10-28T10:00:00Z",
        quotation: { number: "Q-1", version: "1", document_path: "/doc.pdf",
          actions: [{ action: "accept", label: "Accept", ref: "r1" },
                    { action: "decline", label: "Decline", ref: "r1" }] },
      },
    ]);
    const root = await mounted(client, "acme-b");
    expect(root.textContent).toContain("<script>x</script>");
    expect(root.querySelector("script")).toBeNull();
    const labels = Array.from(root.querySelectorAll("button")).map((b) => b.textContent);
    expect(labels).toEqual(expect.arrayContaining(["Download PDF", "Accept", "Decline"]));
  });

  it("keeps working when browser storage is blocked", () => {
    const spy = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    saveToken("acme-c", "cs_memory");
    expect(loadToken("acme-c")).toBe("cs_memory");
    spy.mockRestore();
  });
});
