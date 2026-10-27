export interface TenantInfo {
  tenant_id: string;
  name: string;
  roles: string[];
  permissions: string[];
}

export interface Session {
  subject: string;
  provider: string;
  expires_at: string;
  csrf_token: string;
  tenants: TenantInfo[];
}

export interface AuthConfig {
  provider: "dev" | "disabled";
  dev_subjects: string[];
}

export type Permission =
  | "quotations:view"
  | "quotations:draft"
  | "quotations:approve"
  | "tenant:manage"
  | "enquiries:view"
  | "integrations:manage";
