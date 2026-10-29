import { useCurrentTenant } from "@/features/tenant";
import { dateTime } from "@/shared/lib/format";
import { ErrorMessage } from "@/shared/ui/QueryState";

import { useResendMessage } from "../../hooks/useConversations";
import type { ThreadMessage } from "../../model/types";
import { authorLabel, deliveryLabel } from "../../services/conversationService";

/**
 * Customer text is shown as plain text only (React escapes it; no links are made). A failed
 * customer message can be sent again by administrators and sales operators (phase 5).
 */
export function MessageThread({ messages }: { messages: ThreadMessage[] }) {
  const { can } = useCurrentTenant();
  const resend = useResendMessage();
  const mayResend = can("messages:resend");
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
            {mayResend && message.can_resend && message.outbound_message_id && (
              <button
                disabled={resend.isPending}
                onClick={() => resend.mutate(message.outbound_message_id!)}
              >
                Send again
              </button>
            )}
          </li>
        );
      })}
      <ErrorMessage message={resend.error?.message} />
    </ol>
  );
}
