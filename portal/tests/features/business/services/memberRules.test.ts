import { describe, expect, it } from "vitest";

import type { Member } from "@/features/business/model/types";
import { isLastAdministrator, toggleRole } from "@/features/business/services/memberRules";

function member(id: string, roles: string[]): Member {
  return { user_id: id, email: `${id}@x.example`, display_name: null, roles, is_you: false };
}

describe("memberRules", () => {
  it("knows the last administrator", () => {
    const ana = member("ana", ["administrator", "approver"]);
    const bo = member("bo", ["sales_operator"]);
    expect(isLastAdministrator([ana, bo], ana)).toBe(true);
    expect(isLastAdministrator([ana, bo], bo)).toBe(false);
    const cy = member("cy", ["administrator"]);
    expect(isLastAdministrator([ana, bo, cy], ana)).toBe(false);
  });

  it("toggles roles in a stable order", () => {
    expect(toggleRole(["viewer"], "approver")).toEqual(["approver", "viewer"]);
    expect(toggleRole(["approver", "viewer"], "viewer")).toEqual(["approver"]);
  });
});
