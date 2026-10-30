import { Building2, KeyRound, Percent, Plug, Users, type LucideIcon } from "lucide-react";

import type { Permission } from "@/features/auth";

export interface SettingsSection {
  /** Relative to /settings. */
  path: string;
  label: string;
  description: string;
  icon: LucideIcon;
  permission: Permission;
}

// The settings sections (ADR 0025). A new section: one entry here plus its route in a
// feature's settings routes (mounted under /settings in app/router.tsx).
export const SETTINGS_SECTIONS: readonly SettingsSection[] = [
  {
    path: "business",
    label: "Business",
    description: "Name, address and what your quotes show",
    icon: Building2,
    permission: "tenant:manage",
  },
  {
    path: "pricing",
    label: "Pricing",
    description: "Currency, tax and how long quotes are valid",
    icon: Percent,
    permission: "tenant:manage",
  },
  {
    path: "members",
    label: "People",
    description: "Invite colleagues and choose what they can do",
    icon: Users,
    permission: "members:manage",
  },
  {
    path: "integrations",
    label: "Integrations",
    description: "Telegram, website chat and other tools",
    icon: Plug,
    permission: "integrations:manage",
  },
  {
    path: "api-keys",
    label: "API keys",
    description: "Let your own software send requests",
    icon: KeyRound,
    permission: "integrations:manage",
  },
];

export function visibleSettings(can: (permission: Permission) => boolean): SettingsSection[] {
  return SETTINGS_SECTIONS.filter((section) => can(section.permission));
}
