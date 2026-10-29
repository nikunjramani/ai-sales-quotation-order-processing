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
  /** Phase 5, administrators only: what the tool reported, and the step left to do. */
  detail?: string | null;
  pending?: PendingAction | null;
}

export type PendingActionKind = "open_url" | "provider_page" | "show_steps" | "fill_form";

/** The one step a business still has to do before a one-click tool works. */
export interface PendingAction {
  action_id: string;
  kind: PendingActionKind;
  title: string;
  /** One-time values (a link code) are filled in only in the answer that created them. */
  steps: string[];
  url: string | null;
  form_schema: JsonSchema | null;
  expires_at: string | null;
  once: Record<string, string>;
}

/** The part of JSON Schema the setup forms use (an object with typed properties). */
export interface JsonSchema {
  type?: string;
  title?: string;
  required?: string[];
  properties?: Record<string, JsonSchemaField>;
}

export interface JsonSchemaField {
  type?: "string" | "number" | "integer" | "boolean";
  title?: string;
  description?: string;
  format?: string;
  writeOnly?: boolean;
  enum?: string[];
  default?: string | number | boolean;
}

export interface EnableResult {
  connection: Connection;
  pending: PendingAction | null;
  detail: string | null;
}

export interface ConnectionTest {
  ok: boolean;
  detail: string | null;
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
  /** hosted_chat: website chat (phase 4); one_click: we set up the tool (phase 5). */
  kind: "hosted_chat" | "one_click";
  purposes: Purpose[];
  free: boolean;
  cost_note: string;
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
  /** How to send the code, in the tool's words; url: e.g. a deep link (phase 5). */
  hint?: { text: string; url: string | null } | null;
}
