import {
  FileText,
  House,
  MessageCircle,
  Package,
  Rocket,
  Settings,
  Truck,
  UserRoundSearch,
  type LucideIcon,
} from "lucide-react";

import type { Permission } from "@/features/auth";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Shown when the person has any of these permissions; no list means everyone. */
  show?: Permission[];
  /** Shown in the phone's bottom bar; the rest go under "More". */
  primary?: boolean;
}

// Plain words for the menu (user decision 2026-10-30, ADR 0025). The URLs are unchanged.
export const NAVIGATION: readonly NavItem[] = [
  { to: "/home", label: "Home", icon: House, primary: true },
  { to: "/quotations", label: "Quotes", icon: FileText, primary: true },
  { to: "/inbox", label: "Messages", icon: MessageCircle, show: ["conversations:view"], primary: true },
  { to: "/enquiries", label: "Customer requests", icon: UserRoundSearch },
  { to: "/orders", label: "Orders", icon: Truck, show: ["orders:view"], primary: true },
  { to: "/catalogue", label: "Products", icon: Package, show: ["catalogue:view"] },
  {
    to: "/settings",
    label: "Settings",
    icon: Settings,
    show: ["tenant:manage", "members:manage", "integrations:manage"],
  },
];

export const SETUP_ITEM: NavItem = { to: "/setup", label: "Get started", icon: Rocket };

/** The menu this person sees: only what their role can open, plus Get started while setting up. */
export function visibleNavigation(
  can: (permission: Permission) => boolean,
  settingUp: boolean,
): NavItem[] {
  const items = NAVIGATION.filter((item) => !item.show || item.show.some((permission) => can(permission)));
  return settingUp ? [SETUP_ITEM, ...items] : items;
}
