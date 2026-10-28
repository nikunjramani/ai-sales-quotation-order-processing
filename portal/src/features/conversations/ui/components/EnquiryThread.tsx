import { QueryState } from "@/shared/ui/QueryState";

import { useEnquiryMessages } from "../../hooks/useConversations";
import { MessageThread } from "./MessageThread";

/** Every message of one enquiry (used on the quotation page). */
export function EnquiryThread({ enquiryId }: { enquiryId: string }) {
  const messages = useEnquiryMessages(enquiryId);
  return (
    <QueryState isLoading={messages.isLoading} error={messages.error}>
      <MessageThread messages={messages.data ?? []} />
    </QueryState>
  );
}
