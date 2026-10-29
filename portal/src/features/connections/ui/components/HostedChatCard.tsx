import { useState } from "react";

import { useAvailableTools, useHostedChat } from "../../hooks/useConnections";
import type { Connection } from "../../model/types";
import { originsFromText } from "../../services/connectionService";

/**
 * Website chat (phase 4): one click gives a chat link and a snippet for the business's
 * website. Administrators choose the websites allowed to embed it and a greeting, may change
 * the address once, and can switch the chat off.
 */
export function HostedChatCard({ connections }: { connections: Connection[] }) {
  const available = useAvailableTools(true);
  const chat = useHostedChat();
  const enabled = connections.filter((item) => item.chat !== null);
  const missing = (available.data ?? []).filter(
    (tool) =>
      tool.kind === "hosted_chat" &&
      !enabled.some((item) => item.provider_key === tool.provider_key),
  );
  return (
    <section className="card">
      <h2>Chat on your website</h2>
      {missing.map((tool) => (
        <button
          key={tool.provider_key}
          disabled={chat.enable.isPending}
          onClick={() => chat.enable.mutate(tool.provider_key)}
        >
          Enable {tool.provider_name}
        </button>
      ))}
      {chat.enable.error && <p className="error">{chat.enable.error.message}</p>}
      {enabled.map((item) => (
        <ChatSettings key={item.connection_id} connection={item} />
      ))}
    </section>
  );
}

function ChatSettings({ connection }: { connection: Connection }) {
  const settings = connection.chat!;
  const chat = useHostedChat();
  const [origins, setOrigins] = useState(settings.allowed_origins.join("\n"));
  const [greeting, setGreeting] = useState(settings.greeting);
  const [handle, setHandle] = useState(settings.handle);
  const active = connection.status === "active";
  const error = chat.settings.error ?? chat.address.error ?? chat.active.error;
  return (
    <div>
      <h3>
        {connection.provider_name} {active ? "" : "(switched off)"}
      </h3>
      <p>
        Chat link: <a href={settings.chat_link} target="_blank" rel="noreferrer">{settings.chat_link}</a>
      </p>
      <p className="small">Put this on your website, before &lt;/body&gt;:</p>
      <pre className="snippet">{settings.snippet}</pre>
      <label>
        Websites allowed to show the chat (one per line, e.g. https://www.example.com)
        <textarea value={origins} rows={3} onChange={(event) => setOrigins(event.target.value)} />
      </label>
      <label>
        Greeting
        <input value={greeting} maxLength={300} onChange={(event) => setGreeting(event.target.value)} />
      </label>
      <button
        disabled={chat.settings.isPending}
        onClick={() =>
          chat.settings.mutate({
            id: connection.connection_id,
            allowed_origins: originsFromText(origins),
            greeting,
          })
        }
      >
        Save
      </button>
      {!settings.address_changed && (
        <p>
          <label>
            Chat address (can be changed once; the old link then stops working)
            <input value={handle} maxLength={64} onChange={(event) => setHandle(event.target.value)} />
          </label>
          <button
            className="secondary"
            disabled={chat.address.isPending || handle === settings.handle}
            onClick={() => chat.address.mutate({ id: connection.connection_id, handle })}
          >
            Change address
          </button>
        </p>
      )}
      <button
        className="secondary"
        disabled={chat.active.isPending}
        onClick={() => chat.active.mutate({ id: connection.connection_id, active: !active })}
      >
        {active ? "Switch the chat off" : "Switch the chat on"}
      </button>
      {error && <p className="error">{error.message}</p>}
    </div>
  );
}
