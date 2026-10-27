import type { BusinessStatus } from "@/features/auth";

export interface NewBusiness {
  name: string;
  country: string;
  time_zone: string;
  quote_validity_days: number;
  /** Each may be "set later" (null). Decimals travel as strings, never floats. */
  pricing: { currency: string | null; tax_rate: string | null } | null;
}

export interface BusinessProfile {
  legal_name: string | null;
  address: string | null;
  tax_id_label: string | null;
  tax_id: string | null;
  has_logo: boolean;
  version: number;
}

export interface BusinessSettings {
  tenant_id: string;
  name: string;
  country: string | null;
  time_zone: string | null;
  status: BusinessStatus;
  went_live_at: string | null;
  profile: BusinessProfile;
}

export interface ProfileInput {
  legal_name: string | null;
  address: string | null;
  tax_id_label: string | null;
  tax_id: string | null;
  expected_version: number;
}

export type RoundingMode = "half_up" | "half_even";

export interface PricingPolicy {
  currency: string | null;
  minor_units: number | null;
  rounding_mode: RoundingMode | null;
  tax_rate: string | null;
  max_price_age_seconds: number | null;
  max_stock_age_seconds: number | null;
  quote_validity_days: number;
  complete: boolean;
  version: number;
}

export interface PricingInput {
  currency: string;
  minor_units: number;
  rounding_mode: RoundingMode;
  tax_rate: string;
  max_price_age_seconds: number;
  max_stock_age_seconds: number;
  quote_validity_days: number;
  expected_version: number;
}

export type SetupItemKey =
  | "business_details"
  | "pdf_details"
  | "pricing"
  | "approver"
  | "product_source"
  | "customer_channel"
  | "test_enquiry";

export interface SetupItem {
  key: SetupItemKey;
  done: boolean;
  required: boolean;
}

export interface SetupChecklist {
  status: BusinessStatus;
  items: SetupItem[];
  can_go_live: boolean;
}

export interface Member {
  user_id: string;
  email: string | null;
  display_name: string | null;
  roles: string[];
  is_you: boolean;
}

export interface Invitation {
  invitation_id: string;
  email: string;
  roles: string[];
  status: "pending" | "accepted" | "revoked" | "expired";
  email_status: string;
  expires_at: string | null;
  invited_by: string;
  created_at: string;
}

export interface ApiKeySummary {
  key_id: string;
  name: string;
  role: string;
  created_at: string;
  created_by: string | null;
  revoked_at: string | null;
}

/** Returned once at creation; never cached or stored. */
export interface NewApiKey {
  key_id: string;
  token: string;
}
