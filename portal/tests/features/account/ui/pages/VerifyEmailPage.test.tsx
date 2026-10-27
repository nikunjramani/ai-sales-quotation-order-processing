import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { INVALID_LINK } from "@/features/account/services/links";
import { VerifyEmailPage } from "@/features/account/ui/pages/VerifyEmailPage";

import {
  jsonResponse,
  renderWithProviders,
  testQueryClient,
} from "../../../../support/renderWithProviders";

const TOKEN = "ZO9jh--ZeT9NVYflaXDdAIhotSsPGydbQi0pJ8DyTyI";

describe("VerifyEmailPage", () => {
  it("sends the link's token once, in the body, never in a URL", async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(200, { status: "verified" }));
    vi.stubGlobal("fetch", fetch);
    renderWithProviders(<VerifyEmailPage />, {
      client: testQueryClient(null),
      path: `/verify-email?token=${TOKEN}`,
    });
    expect(await screen.findByText("Your email address is confirmed.")).toBeTruthy();
    const verifyCalls = fetch.mock.calls.filter(([url]) => url === "/api/v1/auth/verify-email");
    expect(verifyCalls).toHaveLength(1);
    expect(JSON.parse(String(verifyCalls[0]?.[1]?.body))).toEqual({ token: TOKEN });
    expect(fetch.mock.calls.some(([url]) => String(url).includes(TOKEN))).toBe(false);
  });

  it("explains an unusable link", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(400, { detail: "x" })));
    renderWithProviders(<VerifyEmailPage />, {
      client: testQueryClient(null),
      path: `/verify-email?token=${TOKEN}`,
    });
    expect(await screen.findByText(INVALID_LINK)).toBeTruthy();
  });
});
