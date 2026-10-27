import { NavLink, useNavigate } from "react-router";

import { useLogout, useSession, type Permission } from "@/features/auth";
import { TenantSwitcher, useCurrentTenant } from "@/features/tenant";

const NAVIGATION: { to: string; label: string; show?: Permission[] }[] = [
  { to: "/quotations", label: "Quotations" },
  { to: "/enquiries", label: "Enquiries" },
  { to: "/connections", label: "Connections" },
  { to: "/settings", label: "Settings", show: ["tenant:manage", "members:manage", "integrations:manage"] },
];

export function TopBar() {
  const session = useSession();
  const { tenant, can } = useCurrentTenant();
  const logout = useLogout();
  const navigate = useNavigate();
  const links = tenant
    ? NAVIGATION.filter((item) => !item.show || item.show.some((permission) => can(permission)))
    : [];
  if (tenant?.status === "setting_up" && can("tenant:manage")) {
    links.unshift({ to: "/setup", label: "Setup" });
  }
  const user = session.data?.user;
  return (
    <header className="topbar">
      <nav>
        {links.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "link active" : "link")}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="who">
        <TenantSwitcher />
        <NavLink to="/profile" className="link small">
          {user?.display_name ?? user?.email ?? session.data?.subject}
        </NavLink>
        {tenant && <span className="muted small">({tenant.roles.join(", ")})</span>}
        <button
          className="secondary"
          disabled={logout.isPending}
          onClick={() => logout.mutate(undefined, { onSettled: () => navigate("/login") })}
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
