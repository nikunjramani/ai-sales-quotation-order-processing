import { Ellipsis, X } from "lucide-react";
import { useState } from "react";
import { NavLink } from "react-router";

import { useCurrentTenant } from "@/features/tenant";

import { visibleNavigation, type NavItem } from "./navigation";

function useMenu(): NavItem[] {
  const { tenant, can } = useCurrentTenant();
  if (!tenant) return [];
  return visibleNavigation(can, tenant.status === "setting_up" && can("tenant:manage"));
}

function MenuLink({ item, onClick }: { item: NavItem; onClick?: () => void }) {
  const Icon = item.icon;
  return (
    <NavLink to={item.to} onClick={onClick} className={({ isActive }) => (isActive ? "nav-item active" : "nav-item")}>
      <Icon size={22} aria-hidden="true" />
      <span>{item.label}</span>
    </NavLink>
  );
}

/** The menu on the left for wider screens (hidden on phones by CSS). */
export function SideNav() {
  const items = useMenu();
  if (!items.length) return null;
  return (
    <nav className="sidenav" aria-label="Main menu">
      {items.map((item) => (
        <MenuLink key={item.to} item={item} />
      ))}
    </nav>
  );
}

/** The phone's bottom bar: the most-used screens, and "More" for everything else. */
export function BottomNav() {
  const items = useMenu();
  const [open, setOpen] = useState(false);
  if (!items.length) return null;
  const primary = items.filter((item) => item.primary).slice(0, 4);
  const rest = items.filter((item) => !primary.includes(item));
  return (
    <>
      {open && (
        <div className="more-sheet" role="dialog" aria-label="More pages">
          <div className="more-head">
            <strong>More pages</strong>
            <button className="icon-button" aria-label="Close" onClick={() => setOpen(false)}>
              <X size={22} aria-hidden="true" />
            </button>
          </div>
          {rest.map((item) => (
            <MenuLink key={item.to} item={item} onClick={() => setOpen(false)} />
          ))}
        </div>
      )}
      <nav className="bottomnav" aria-label="Quick menu">
        {primary.map((item) => (
          <MenuLink key={item.to} item={item} onClick={() => setOpen(false)} />
        ))}
        {rest.length > 0 && (
          <button className={open ? "nav-item active" : "nav-item"} aria-expanded={open} onClick={() => setOpen(!open)}>
            <Ellipsis size={22} aria-hidden="true" />
            <span>More</span>
          </button>
        )}
      </nav>
    </>
  );
}
