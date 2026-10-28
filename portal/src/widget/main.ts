// Website chat widget (phase 4), built as one file: dist/widget/widget.js.
//
// On a business's website:  <script src="https://<our address>/chat/widget.js" data-chat="<handle>" async></script>
// shows a chat bubble. Our hosted page /chat/<handle> loads the same file with
// data-mode="page" to fill the window. The API address is where the script came from.

import { createChatClient } from "./api/chatClient";
import { mountChat } from "./ui/chatView";

function boot(): void {
  const script =
    (document.currentScript as HTMLScriptElement | null) ??
    document.querySelector<HTMLScriptElement>("script[data-chat]");
  const handle = script?.dataset.chat;
  if (!script || !handle) return;
  const baseUrl = new URL(script.src, window.location.href).origin;
  const fullPage = script.dataset.mode === "page";
  const host = document.createElement("div");
  document.body.append(host);
  void mountChat(host, createChatClient(baseUrl, handle), handle, fullPage);
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();
