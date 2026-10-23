import { act } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useCurrentTenant, useTenantStore } from "@/features/tenant";

import {
  TEST_SESSION,
  renderHookWithProviders,
  testQueryClient,
} from "../../../support/renderWithProviders";

const TWO_TENANTS = {
  ...TEST_SESSION,
  tenants: [
    ...TEST_SESSION.tenants,
    { tenant_id: "t2", name: "Demo Office", roles: ["viewer"], permissions: ["quotations:view"] },
  ],
};

describe("useCurrentTenant", () => {
  beforeEach(() => useTenantStore.getState().clear());

  it("uses the first membership until the person chooses another", () => {
    const { result } = renderHookWithProviders(useCurrentTenant, {
      client: testQueryClient(TWO_TENANTS),
    });
    expect(result.current.tenant?.tenant_id).toBe("t1");
    expect(result.current.can("quotations:approve")).toBe(true);
    act(() => result.current.selectTenant("t2"));
    expect(result.current.tenant?.tenant_id).toBe("t2");
    expect(result.current.can("quotations:approve")).toBe(false);
  });

  it("ignores a remembered business the person no longer belongs to", () => {
    useTenantStore.getState().selectTenant("removed-tenant");
    const { result } = renderHookWithProviders(useCurrentTenant);
    expect(result.current.tenant?.tenant_id).toBe("t1");
  });

  it("has no tenant and no permissions when signed out", () => {
    const { result } = renderHookWithProviders(useCurrentTenant, { client: testQueryClient(null) });
    expect(result.current.tenant).toBeNull();
    expect(result.current.can("quotations:view")).toBe(false);
  });
});
