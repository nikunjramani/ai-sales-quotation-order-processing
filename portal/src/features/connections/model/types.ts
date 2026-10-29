export type Purpose =
  | "customer_messages"
  | "manager_approvals"
  | "catalogue"
  | "payments"
  | "orders";

export type ConnectionStatus = "setting_up" | "active" | "error" | "disabled";

/** One of the business's tools (API, simulated phone, later Telegram, email...). */
export interface Connection {
  connection_id: string;
  provider_key: string;
  provider_name: string;
  display_name: string;
  purposes: Purpose[];
  status: ConnectionStatus;
  /** Technical error, shown to administrators only (null for others). */
  last_error: string | null;
  created_at: string;
  /** Hosted chat (website chat, phase 4), administrators only. */
  chat: HostedChat | null;
}

export interface HostedChat {
  handle: string;
  chat_link: string;
  snippet: string;
  allowed_origins: string[];
  greeting: string;
  address_changed: boolean;
}

/** A tool an administrator can enable with one click. */
export interface AvailableTool {
  provider_key: string;
  provider_name: string;
}

/** A manager's own account linked on one connection, so approval requests reach it. */
export interface Binding {
  binding_id: string;
  subject: string;
  channel: string;
  connection_id: string;
  connection_ref: string;
  connection_name: string;
  external_user_id: string;
  created_at: string;
  revoked_at: string | null;
}

export interface Enrollment {
  connection_id: string;
  channel: string;
  code: string;
  expires_at: string;
}
