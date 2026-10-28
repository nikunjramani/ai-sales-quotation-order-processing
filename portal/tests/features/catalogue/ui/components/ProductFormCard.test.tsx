import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProductFormCard } from "@/features/catalogue/ui/components/ProductFormCard";

import { jsonResponse, renderWithProviders } from "../../../../support/renderWithProviders";

const UNITS = ["box", "each", "kg", "metre"];

describe("ProductFormCard", () => {
  it("shows the form's own problem before sending anything", async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(200, []));
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<ProductFormCard units={UNITS} product={null} editable onSaved={() => undefined} />);
    await userEvent.type(screen.getByLabelText("SKU (product code)"), "BOLT 1");
    await userEvent.type(screen.getByLabelText("Name (customers see this)"), "Bolt");
    await userEvent.click(screen.getByRole("button", { name: "Add product" }));
    expect(screen.getByRole("alert").textContent).toContain("SKU");
    expect(fetch.mock.calls.every(([, init]) => (init as RequestInit | undefined)?.method !== "POST")).toBe(true);
  });

  it("shows the server's field problem", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((_url: string, init?: RequestInit) =>
        Promise.resolve(
          init?.method === "POST"
            ? jsonResponse(409, { detail: { code: "sku_taken", message: "A product with SKU BOLT-1 already exists" } })
            : jsonResponse(200, []),
        ),
      ),
    );
    renderWithProviders(<ProductFormCard units={UNITS} product={null} editable onSaved={() => undefined} />);
    await userEvent.type(screen.getByLabelText("SKU (product code)"), "BOLT-1");
    await userEvent.type(screen.getByLabelText("Name (customers see this)"), "Bolt");
    await userEvent.click(screen.getByRole("button", { name: "Add product" }));
    expect((await screen.findByRole("alert")).textContent).toContain("already exists");
  });

  it("has no save button when read-only", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, [])));
    renderWithProviders(<ProductFormCard units={UNITS} product={null} editable={false} onSaved={() => undefined} />);
    expect(screen.queryByRole("button", { name: "Add product" })).toBeNull();
  });
});
