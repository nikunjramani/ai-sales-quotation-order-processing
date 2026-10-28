/** A business's life (phase 2): set up, then Go live; suspended only by the platform. */
export type BusinessStatus = "setting_up" | "active" | "suspended";

export interface TenantInfo {
  tenant_id: string;
  name: string;
  status: BusinessStatus;
  roles: string[];
  permissions: string[];
}

/** The person signed in (null for demo people who exist only for the dev login). */
export interface SessionUser {
  user_id: string;
  email: string | null;
  display_name: string | null;
  email_verified: boolean;
}

export interface Session {
  subject: string;
  provider: string;
  expires_at: string;
  csrf_token: string;
  user: SessionUser | null;
  tenants: TenantInfo[];
}

export interface AuthConfig {
  password_login: true;
  dev_login: boolean;
  dev_subjects: string[];
}

export type Permission =
  | "quotations:view"
  | "quotations:draft"
  | "quotations:approve"
  | "tenant:manage"
  | "enquiries:view"
  | "integrations:manage"
  | "members:manage"
  | "catalogue:view"
  | "catalogue:manage";
