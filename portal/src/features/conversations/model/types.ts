// Customers and conversations (phase 4), as the API returns them.

export interface ConversationSummary {
  conversation_id: string;
  contact_id: string;
  contact_name: string | null;
  provider_key: string;
  connection_name: string;
  last_text: string;
  last_direction: "inbound" | "outbound";
  last_at: string;
  enquiry_id: string | null;
  enquiry_status: string | null;
  quotation_id: string | null;
  quotation_status: string | null;
}

export interface ThreadMessage {
  seq: number;
  direction: "inbound" | "outbound";
  author: "customer" | "system" | "staff";
  text: string;
  at: string;
  enquiry_id: string | null;
  template_key: string | null;
  outbound_status: string | null;
  outbound_error: string | null;
  /** Phase 5: our message's ID, and whether staff may send it again (failed, not resent). */
  outbound_message_id?: string | null;
  can_resend?: boolean;
}

export interface Identity {
  identity_id: string;
  provider_key: string;
  connection_name: string;
  external_id: string;
  verified: boolean;
  consent: "implied" | "opted_in" | "opted_out";
}

export interface ConversationDetail {
  conversation: ConversationSummary;
  identity: Identity;
  messages: ThreadMessage[];
}

export interface Contact {
  contact_id: string;
  name: string | null;
  company: string | null;
  email: string | null; // masked for viewers
  phone: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  identities: number;
  last_activity: string | null;
}

export interface ContactEnquiry {
  enquiry_id: string;
  status: string;
  received_at: string;
  quotation_id: string | null;
  quotation_status: string | null;
}

export interface ContactDetail {
  contact: Contact;
  identities: Identity[];
  conversations: string[];
  enquiries: ContactEnquiry[];
  suggestions: Contact[];
}

export interface CustomerMessages {
  acknowledge_enquiries: boolean;
}
