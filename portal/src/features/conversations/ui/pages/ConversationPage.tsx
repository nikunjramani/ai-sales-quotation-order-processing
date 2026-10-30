import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router";

import { QueryState } from "@/shared/ui/QueryState";
import { StatusBadge } from "@/shared/ui/StatusBadge";

import { useConversation } from "../../hooks/useConversations";
import { consentLabel } from "../../services/conversationService";
import { MessageThread } from "../components/MessageThread";

export function ConversationPage() {
  const { conversationId = "" } = useParams();
  const found = useConversation(conversationId);
  const data = found.data;
  return (
    <section>
      <p>
        <Link className="link" to="/inbox">
          <ArrowLeft size={18} aria-hidden="true" /> All messages
        </Link>
      </p>
      <QueryState isLoading={found.isLoading} error={found.error}>
        {data && (
          <>
            <h1>{data.conversation.contact_name ?? "Unknown customer"}</h1>
            <p className="muted small">
              {data.identity.connection_name} · {consentLabel(data.identity.consent)} ·{" "}
              <Link to={`/contacts/${data.conversation.contact_id}`}>Contact</Link>
            </p>
            {data.conversation.quotation_id && (
              <p>
                <Link to={`/quotations/${data.conversation.quotation_id}`}>Quotation</Link>{" "}
                {data.conversation.quotation_status && (
                  <StatusBadge status={data.conversation.quotation_status} />
                )}
              </p>
            )}
            <MessageThread messages={data.messages} />
            <p className="muted small">Replies typed by staff come later (D16).</p>
          </>
        )}
      </QueryState>
    </section>
  );
}
