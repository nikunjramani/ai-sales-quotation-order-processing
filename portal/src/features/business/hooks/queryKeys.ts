// Every key starts with the business, so switching business never shows another one's data.
export const businessKeys = {
  settings: (tenantId: string) => ["tenants", tenantId, "business"] as const,
  pricing: (tenantId: string) => ["tenants", tenantId, "pricing"] as const,
  setup: (tenantId: string) => ["tenants", tenantId, "setup"] as const,
  members: (tenantId: string) => ["tenants", tenantId, "members"] as const,
  invitations: (tenantId: string) => ["tenants", tenantId, "invitations"] as const,
  apiKeys: (tenantId: string) => ["tenants", tenantId, "api-keys"] as const,
};
