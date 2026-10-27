import { apiUrl, http, tenantPath } from "@/shared/api/httpClient";

import type {
  BusinessSettings,
  NewBusiness,
  PricingInput,
  PricingPolicy,
  ProfileInput,
  SetupChecklist,
} from "../model/types";

export const businessRepository = {
  create: (input: NewBusiness) =>
    http<{ tenant_id: string }>("/businesses", { method: "POST", body: input }),

  settings: (tenantId: string) => http<BusinessSettings>(tenantPath(tenantId, "/business")),

  updateDetails: (tenantId: string, input: { name: string; country: string; time_zone: string }) =>
    http<void>(tenantPath(tenantId, "/business"), { method: "PUT", body: input }),

  updateProfile: (tenantId: string, input: ProfileInput) =>
    http<{ version: number }>(tenantPath(tenantId, "/business/profile"), {
      method: "PUT",
      body: input,
    }),

  uploadLogo: (tenantId: string, contentBase64: string) =>
    http<void>(tenantPath(tenantId, "/business/logo"), {
      method: "PUT",
      body: { content_base64: contentBase64 },
    }),

  removeLogo: (tenantId: string) =>
    http<void>(tenantPath(tenantId, "/business/logo"), { method: "DELETE" }),

  /** The browser loads the logo itself (an <img>), with the session cookie. */
  logoUrl: (tenantId: string, version: number) =>
    `${apiUrl(tenantPath(tenantId, "/business/logo"))}?v=${version}`,

  pricing: (tenantId: string) => http<PricingPolicy>(tenantPath(tenantId, "/pricing-policy")),

  updatePricing: (tenantId: string, input: PricingInput) =>
    http<{ version: number }>(tenantPath(tenantId, "/pricing-policy"), {
      method: "PUT",
      body: input,
    }),

  setup: (tenantId: string) => http<SetupChecklist>(tenantPath(tenantId, "/setup")),

  goLive: (tenantId: string) =>
    http<SetupChecklist>(tenantPath(tenantId, "/go-live"), { method: "POST" }),
};
