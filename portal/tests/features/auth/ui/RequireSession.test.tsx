import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Route, Routes } from "react-router";

import { RequireSession } from "@/features/auth";

import { renderWithProviders, testQueryClient } from "../../../support/renderWithProviders";

function screens() {
  return (
    <Routes>
      <Route path="/login" element={<p>login page</p>} />
      <Route
        path="/quotations"
        element={
          <RequireSession>
            <p>private page</p>
          </RequireSession>
        }
      />
    </Routes>
  );
}

describe("RequireSession", () => {
  it("shows the page to a signed-in person", () => {
    renderWithProviders(screens(), { path: "/quotations" });
    expect(screen.getByText("private page")).toBeTruthy();
  });

  it("sends a signed-out person to the login page", () => {
    renderWithProviders(screens(), { path: "/quotations", client: testQueryClient(null) });
    expect(screen.getByText("login page")).toBeTruthy();
    expect(screen.queryByText("private page")).toBeNull();
  });
});
