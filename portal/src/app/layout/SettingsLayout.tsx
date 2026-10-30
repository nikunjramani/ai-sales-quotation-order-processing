import { Settings } from "lucide-react";
import { Navigate, NavLink, Outlet, useLocation } from "react-router";

import { useCurrentTenant } from "@/features/tenant";
import { PageHeader } from "@/shared/ui/PageHeader";

import { visibleSettings } from "./settingsNavigation";

/**
 * The settings frame (ADR 0025): the section list on the left on wide screens (icon, name and
 * one line on what it is for), scrollable pill tabs on phones, and the section on the right.
 * Only the sections the person's role may open are listed.
 */
export function SettingsLayout() {
  const { can } = useCurrentTenant();
  const sections = visibleSettings(can);
  const { pathname } = useLocation();
  const first = sections[0];
  if (pathname.replace(/\/+$/, "") === "/settings") {
    if (first) return <Navigate to={`/settings/${first.path}`} replace />;
  }
  return (
    <section>
      <PageHeader icon={Settings} title="Settings" hint="Set up your business, the people who work with you and the tools you use." />
      {sections.length === 0 ? (
        <p className="muted">Your role has no settings to change. Ask an Admin.</p>
      ) : (
        <div className="settings">
          <nav className="settings-nav" aria-label="Settings sections">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <NavLink
                  key={section.path}
                  to={`/settings/${section.path}`}
                  className={({ isActive }) => (isActive ? "settings-tab active" : "settings-tab")}
                >
                  <Icon size={22} aria-hidden="true" />
                  <span>
                    <span className="settings-tab-name">{section.label}</span>
                    <span className="settings-tab-hint">{section.description}</span>
                  </span>
                </NavLink>
              );
            })}
          </nav>
          <div className="settings-body">
            <Outlet />
          </div>
        </div>
      )}
    </section>
  );
}
