import { dateTime } from "@/shared/lib/format";

import type { ThreadMessage } from "../../model/types";
import { authorLabel, deliveryLabel } from "../../services/conversationService";

/** Customer text is shown as plain text only (React escapes it; no links are made). */
export function MessageThread({ messages }: { messages: ThreadMessage[] }) {
  if (messages.length === 0) return <p className="muted">No messages yet.</p>;
  return (
    <ol className="thread">
      {messages.map((message) => {
        const delivery = deliveryLabel(message);
        return (
          <li key={message.seq} className={`bubble ${message.direction}`}>
            <span className="muted small">
              {authorLabel(message)} · {dateTime(message.at)}
            </span>
            <p className="message-text">{message.text}</p>
            {delivery && <span className="muted small">{delivery}</span>}
          </li>
        );
      })}
    </ol>
  );
}
