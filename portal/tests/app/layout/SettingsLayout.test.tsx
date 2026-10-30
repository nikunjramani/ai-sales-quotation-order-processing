import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router";
import { describe, expect, it } from "vitest";

import { SettingsLayout } from "@/app/layout/SettingsLayout";

import { renderWithProviders, testQueryClient, TEST_SESSION } from "../../support/renderWithProviders";

const ADMIN = {
  ...TEST_SESSION,
  tenants: [
    {
      ...TEST_SESSION.tenants[0]!,
      roles: ["administrator"],
      permissions: ["tenant:manage", "members:manage", "integrations:manage"],
    },
  ],
};

function renderAt(path: string, session = ADMIN) {
  return renderWithProviders(
    <Routes>
      <Route path="/settings" element={<SettingsLayout />}>
        <Route path="business" element={<p>business section</p>} />
        <Route path="integrations" element={<p>integrations section</p>} />
      </Route>
    </Routes>,
    { client: testQueryClient(session), path },
  );
}

describe("SettingsLayout", () => {
  it("opens the first section and shows every section as a tab", async () => {
    renderAt("/settings");
    expect(await screen.findByText("business section")).toBeTruthy();
    expect(screen.getByRole("link", { name: /Integrations/ })).toBeTruthy();
    expect(screen.getByRole("link", { name: /API keys/ })).toBeTruthy();
  });

  it("tells a role without settings to ask an Admin", () => {
    renderAt("/settings/business", TEST_SESSION); // the test approver has no settings permission
    expect(screen.getByText("Your role has no settings to change. Ask an Admin.")).toBeTruthy();
  });
});
