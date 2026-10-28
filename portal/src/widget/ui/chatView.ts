// The chat UI in plain DOM inside a Shadow DOM (the website's CSS cannot break it, ours cannot
// leak). Every text goes in with textContent: customer and server text is never HTML.

import { ChatError, type ChatClient, type ChatConfig, type ChatMessage } from "../api/chatClient";
import { idempotencyKey, loadToken, saveToken } from "../state/session";

const VISIBLE_POLL_MS = 3000;
const HIDDEN_POLL_MS = 15000;

const STYLE = `
:host { all: initial; font: 14px/1.4 system-ui, sans-serif; color: #222; }
.box { display: flex; flex-direction: column; height: 100%; background: #fff; }
.head { padding: 10px 12px; background: #1d4ed8; color: #fff; font-weight: 600; }
.list { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 8px; }
.msg { max-width: 85%; padding: 8px 10px; border-radius: 10px; white-space: pre-wrap; overflow-wrap: anywhere; }
.inbound { align-self: flex-end; background: #dbeafe; }
.outbound { align-self: flex-start; background: #f3f4f6; }
.card { border: 1px solid #ccc; border-radius: 8px; padding: 8px; margin-top: 6px; }
form { display: flex; flex-direction: column; gap: 6px; padding: 10px; border-top: 1px solid #eee; }
input, textarea, button { font: inherit; padding: 6px 8px; }
button { cursor: pointer; }
.row { display: flex; gap: 6px; }
.error { color: #b91c1c; }
.trap { position: absolute; left: -9999px; }
.bubble { position: fixed; right: 16px; bottom: 16px; width: 360px; max-width: calc(100vw - 32px);
  height: 520px; max-height: calc(100vh - 32px); box-shadow: 0 4px 20px rgba(0,0,0,.2);
  border-radius: 12px; overflow: hidden; }
.closed { height: auto; }
`;

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  props: Partial<HTMLElementTagNameMap[K]> = {},
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  Object.assign(node, props);
  for (const child of children) node.append(child);
  return node;
}

async function readFile(file: File): Promise<{ filename: string; content_type: string; content_base64: string }> {
  const buffer = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  for (const byte of buffer) binary += String.fromCharCode(byte);
  return { filename: file.name, content_type: file.type || "application/octet-stream", content_base64: btoa(binary) };
}

export async function mountChat(host: HTMLElement, client: ChatClient, handle: string, fullPage: boolean) {
  const shadow = host.attachShadow({ mode: "open" });
  shadow.append(element("style", { textContent: STYLE }));
  const box = element("div", { className: fullPage ? "box" : "box bubble" });
  if (fullPage) host.style.height = "100vh";
  shadow.append(box);

  let config: ChatConfig;
  try {
    config = await client.config();
  } catch {
    box.append(element("p", { className: "error", textContent: "This chat is not available." }));
    return;
  }
  const head = element("div", { className: "head", textContent: config.business_name });
  box.append(head);
  const body = element("div", { className: "list" });
  box.append(body);
  let open = fullPage;
  if (!fullPage) {
    head.style.cursor = "pointer";
    const toggle = () => {
      open = !open;
      body.style.display = open ? "" : "none";
      box.classList.toggle("closed", !open);
      for (const form of box.querySelectorAll("form")) form.style.display = open ? "" : "none";
    };
    head.onclick = toggle;
    open = true;
    toggle(); // start closed: only the bubble's title shows
  }

  const token = loadToken(handle);
  if (token) startChat(token);
  else showStartForm();

  function showStartForm() {
    const shownAt = Date.now();
    if (config.greeting) body.append(element("div", { className: "msg outbound", textContent: config.greeting }));
    body.append(element("p", { textContent: "Please tell us who you are. Give an email or a phone number." }));
    const name = element("input", { placeholder: "Your name", required: true, maxLength: 100 });
    const email = element("input", { placeholder: "Email", type: "email", maxLength: 320 });
    const phone = element("input", { placeholder: "Phone with country code, e.g. +91…", maxLength: 40 });
    const trap = element("input", { className: "trap", tabIndex: -1, autocomplete: "off", name: "website" });
    const error = element("p", { className: "error" });
    const form = element("form", {}, name, email, phone, trap, element("button", { textContent: "Start chat" }), error);
    form.onsubmit = async (event) => {
      event.preventDefault();
      if (!email.value.trim() && !phone.value.trim()) {
        error.textContent = "Please give an email address or a phone number";
        return;
      }
      try {
        const started = await client.start({
          name: name.value,
          email: email.value.trim() || undefined,
          phone: phone.value.trim() || undefined,
          website: trap.value,
          form_ms: Date.now() - shownAt,
        });
        saveToken(handle, started.session_token);
        form.remove();
        body.replaceChildren();
        startChat(started.session_token);
      } catch (problem) {
        error.textContent = problem instanceof Error ? problem.message : "Please try again";
      }
    };
    box.append(form);
    form.style.display = open ? "" : "none";
  }

  function startChat(sessionToken: string) {
    let after = 0;
    let timer = 0;
    const text = element("textarea", { rows: 2, maxLength: config.max_message_chars, placeholder: "Type your message" });
    const files = element("input", { type: "file", multiple: true, accept: ".pdf,.txt,.png,.jpg,.jpeg" });
    const error = element("p", { className: "error" });
    const form = element(
      "form",
      {},
      text,
      element("div", { className: "row" }, files, element("button", { textContent: "Send" })),
      error,
    );
    box.append(form);
    form.style.display = open ? "" : "none";

    form.onsubmit = async (event) => {
      event.preventDefault();
      if (!text.value.trim()) return;
      const chosen = Array.from(files.files ?? []);
      if (chosen.length > config.files_per_message || chosen.some((f) => f.size > config.max_file_bytes)) {
        error.textContent = `At most ${config.files_per_message} files of ${config.max_file_bytes / 1048576} MB each`;
        return;
      }
      error.textContent = "";
      try {
        await client.send(sessionToken, text.value, await Promise.all(chosen.map(readFile)), idempotencyKey());
        text.value = "";
        files.value = "";
        void poll();
      } catch (problem) {
        handle401(problem);
        error.textContent = problem instanceof Error ? problem.message : "Please try again";
      }
    };

    function handle401(problem: unknown) {
      if (problem instanceof ChatError && problem.status === 401) {
        saveToken(handle, null);
        window.clearTimeout(timer);
        form.remove();
        body.replaceChildren();
        showStartForm();
      }
    }

    function render(message: ChatMessage) {
      const item = element("div", { className: `msg ${message.direction}`, textContent: message.text });
      const quotation = message.quotation;
      if (quotation) {
        const card = element("div", { className: "card" });
        if (quotation.document_path) {
          const path = quotation.document_path;
          const download = element("button", { textContent: "Download PDF", type: "button" });
          download.onclick = async () => {
            const blob = await client.document(sessionToken, path);
            const link = element("a", { href: URL.createObjectURL(blob), download: `${quotation.number}.pdf` });
            link.click();
          };
          card.append(download, " ");
        }
        for (const action of quotation.actions) {
          const button = element("button", { textContent: action.label, type: "button" });
          button.onclick = async () => {
            if (!window.confirm(`${action.label} quotation ${quotation.number}?`)) return;
            card.querySelectorAll("button").forEach((b) => (b.disabled = true));
            try {
              await client.act(sessionToken, action.ref, action.action);
            } catch (problem) {
              card.append(element("p", { className: "error", textContent: problem instanceof Error ? problem.message : "Please try again" }));
            }
            void poll();
          };
          card.append(button, " ");
        }
        item.append(card);
      }
      body.append(item);
      body.scrollTop = body.scrollHeight;
    }

    async function poll() {
      window.clearTimeout(timer);
      let wait = document.hidden ? HIDDEN_POLL_MS : VISIBLE_POLL_MS;
      try {
        const page = await client.poll(sessionToken, after);
        for (const message of page.messages) render(message);
        after = page.after;
        wait = Math.max(wait, page.poll_ms);
      } catch (problem) {
        handle401(problem);
        if (problem instanceof ChatError && problem.status === 401) return;
        wait = problem instanceof ChatError && problem.retryAfterSeconds ? problem.retryAfterSeconds * 1000 : wait * 2;
      }
      timer = window.setTimeout(poll, wait);
    }
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) void poll();
    });
    void poll();
  }
}
