import { http, tenantPath } from "@/shared/api/httpClient";

import type {
  Contact,
  ContactDetail,
  ConversationDetail,
  ConversationSummary,
  CustomerMessages,
  ThreadMessage,
} from "../model/types";

const id = encodeURIComponent;

export const conversationRepository = {
  inbox: (tenantId: string) => http<ConversationSummary[]>(tenantPath(tenantId, "/conversations")),

  conversation: (tenantId: string, conversationId: string) =>
    http<ConversationDetail>(tenantPath(tenantId, `/conversations/${id(conversationId)}`)),

  enquiryMessages: (tenantId: string, enquiryId: string) =>
    http<ThreadMessage[]>(tenantPath(tenantId, `/enquiries/${id(enquiryId)}/messages`)),

  contacts: (tenantId: string, query: string) =>
    http<Contact[]>(tenantPath(tenantId, "/contacts"), { query: { q: query || undefined } }),

  contact: (tenantId: string, contactId: string) =>
    http<ContactDetail>(tenantPath(tenantId, `/contacts/${id(contactId)}`)),

  /** Moves everything of `contactId` into `intoContactId`. Cannot be undone (D13). */
  merge: (tenantId: string, contactId: string, intoContactId: string) =>
    http<void>(tenantPath(tenantId, `/contacts/${id(contactId)}/merge`), {
      method: "POST",
      body: { into_contact_id: intoContactId },
    }),

  customerMessages: (tenantId: string) =>
    http<CustomerMessages>(tenantPath(tenantId, "/customer-messages")),

  setCustomerMessages: (tenantId: string, value: CustomerMessages) =>
    http<CustomerMessages>(tenantPath(tenantId, "/customer-messages"), { method: "PUT", body: value }),
};
