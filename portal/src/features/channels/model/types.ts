export interface Binding {
  binding_id: string;
  subject: string;
  channel: string;
  connection_id: string;
  external_user_id: string;
  created_at: string;
  revoked_at: string | null;
}

export interface Enrollment {
  channel: string;
  code: string;
  expires_at: string;
}
