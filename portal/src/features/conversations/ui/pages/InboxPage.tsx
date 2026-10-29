import { Link } from "react-router";

import { useCurrentTenant } from "@/features/tenant";
import { dateTime } from "@/shared/lib/format";
import { QueryState } from "@/shared/ui/QueryState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

import { useCustomerMessages, useInbox } from "../../hooks/useConversations";
import { preview } from "../../services/conversationService";

/** Every customer conversation, newest activity first (refreshes every 15 seconds). */
export function InboxPage() {
  const inbox = useInbox();
  const { can } = useCurrentTenant();
  return (
    <section>
      <h1>Inbox</h1>
      <p>
        <Link to="/contacts">Contacts</Link>
      </p>
      {can("tenant:manage") && <AcknowledgementSetting />}
      <QueryState isLoading={inbox.isLoading} error={inbox.error} isEmpty={inbox.data?.length === 0}>
        <ul className="list">
          {inbox.data?.map((item) => (
            <li key={item.conversation_id}>
              <Link className="row" to={`/inbox/${item.conversation_id}`}>
                <span>
                  <strong>{item.contact_name ?? "Unknown customer"}</strong>{" "}
                  <span className="muted small">via {item.connection_name}</span>
                  <br />
                  <span className="quote">
                    {item.last_direction === "outbound" ? "You: " : ""}
                    {preview(item.last_text)}
                  </span>
                  <br />
                  <span className="muted small">{dateTime(item.last_at)}</span>
                </span>
                {item.quotation_status ? (
                  <StatusBadge status={item.quotation_status} />
                ) : (
                  item.enquiry_status && <StatusBadge status={item.enquiry_status} />
                )}
              </Link>
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}

/** D14: "Thanks, we are preparing your quotation." on new enquiries (administrators). */
function AcknowledgementSetting() {
  const { query, save } = useCustomerMessages();
  if (!query.data) return null;
  return (
    <label className="small">
      <input
        type="checkbox"
        checked={query.data.acknowledge_enquiries}
        disabled={save.isPending}
        onChange={(event) => save.mutate(event.target.checked)}
      />{" "}
      Tell customers "we are preparing your quotation" when a new enquiry arrives
    </label>
  );
}
