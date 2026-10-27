import { NavLink, useNavigate } from "react-router";

import { useLogout, useSession } from "@/features/auth";
import { TenantSwitcher, useCurrentTenant } from "@/features/tenant";

const NAVIGATION = [
  { to: "/quotations", label: "Quotations" },
  { to: "/enquiries", label: "Enquiries" },
  { to: "/connections", label: "Connections" },
];

export function TopBar() {
  const session = useSession();
  const { tenant } = useCurrentTenant();
  const logout = useLogout();
  const navigate = useNavigate();
  return (
    <header className="topbar">
      <nav>
        {NAVIGATION.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "link active" : "link")}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="who">
        <TenantSwitcher />
        <span className="muted small">
          {session.data?.subject} ({tenant?.roles.join(", ")})
        </span>
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
