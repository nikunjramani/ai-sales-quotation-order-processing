import { NavLink } from "react-router";

import { useCurrentTenant } from "@/features/tenant";
import type { Permission } from "@/features/auth";

const LINKS: { to: string; label: string; permission: Permission }[] = [
  { to: "/settings/business", label: "Business", permission: "tenant:manage" },
  { to: "/settings/pricing", label: "Pricing", permission: "tenant:manage" },
  { to: "/settings/members", label: "People", permission: "members:manage" },
  { to: "/settings/api-keys", label: "API keys", permission: "integrations:manage" },
];

export function SettingsNav() {
  const { can } = useCurrentTenant();
  return (
    <nav className="tabs">
      {LINKS.filter((link) => can(link.permission)).map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) => (isActive ? "tab active" : "tab")}
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
