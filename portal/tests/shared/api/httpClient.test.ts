import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, http, isApiError, setCsrfToken, tenantPath } from "@/shared/api/httpClient";

import { jsonResponse } from "../../support/renderWithProviders";

describe("http", () => {
  beforeEach(() => setCsrfToken("csrf-123"));

  it("sends the CSRF header on changes but not on reads", async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    vi.stubGlobal("fetch", fetch);
    await http("/things");
    await http("/things", { method: "POST", body: { a: 1 } });
    const [, read] = fetch.mock.calls[0] as [string, RequestInit];
    const [url, write] = fetch.mock.calls[1] as [string, RequestInit];
    expect((read.headers as Record<string, string>)["X-CSRF-Token"]).toBeUndefined();
    expect(url).toBe("/api/v1/things");
    expect(write.credentials).toBe("same-origin");
    expect((write.headers as Record<string, string>)["X-CSRF-Token"]).toBe("csrf-123");
    expect(write.body).toBe('{"a":1}');
  });

  it("repeats list query parameters and skips empty ones", async () => {
    const fetch = vi.fn().mockResolvedValue(jsonResponse(200, []));
    vi.stubGlobal("fetch", fetch);
    await http("/q", { query: { status: ["a", "b"], other: undefined } });
    await http("/q", { query: { status: [] } });
    expect(fetch.mock.calls[0]?.[0]).toBe("/api/v1/q?status=a&status=b");
    expect(fetch.mock.calls[1]?.[0]).toBe("/api/v1/q");
  });

  it("turns error responses into ApiError with the server's message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(409, { detail: { message: "Already decided" } })),
    );
    const failure = await http("/x", { method: "POST" }).catch((error: unknown) => error);
    expect(failure).toBeInstanceOf(ApiError);
    expect(isApiError(failure, 409)).toBe(true);
    expect((failure as ApiError).message).toBe("Already decided");
  });

  it("returns undefined for 204 and encodes tenant paths", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(204, undefined)));
    await expect(http("/x", { method: "DELETE" })).resolves.toBeUndefined();
    expect(tenantPath("a/b", "/quotations")).toBe("/tenants/a%2Fb/quotations");
  });
});
