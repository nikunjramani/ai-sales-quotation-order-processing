import { describe, expect, it } from "vitest";

import type { AvailableTool, Connection, ConnectionStatus } from "@/features/connections/model/types";
import { COMING_SOON } from "@/features/connections/services/comingSoon";
import {
  comingSoon,
  groupConnections,
  groupSummary,
} from "@/features/connections/services/connectionService";

function connection(id: string, provider: string, status: ConnectionStatus): Connection {
  return {
    connection_id: id,
    provider_key: provider,
    provider_name: provider === "api" ? "API (customer systems)" : "Telegram",
    display_name: id,
    purposes: provider === "api" ? ["customer_messages"] : ["manager_approvals", "customer_messages"],
    status,
    last_error: null,
    created_at: "2026-10-30T10:00:00Z",
    chat: null,
  };
}

describe("groupConnections", () => {
  it("puts each kind of tool in one card and keeps switched-off ones apart", () => {
    const groups = groupConnections([
      connection("k1", "api", "active"),
      connection("t1", "telegram", "error"),
      connection("k2", "api", "disabled"),
      connection("k3", "api", "active"),
    ]);
    expect(groups.map((group) => group.providerKey)).toEqual(["api", "telegram"]);
    const api = groups[0]!;
    expect(api.current.map((item) => item.connection_id)).toEqual(["k1", "k3"]);
    expect(api.switchedOff.map((item) => item.connection_id)).toEqual(["k2"]);
    expect(groupSummary(api)).toBe("2 active");
    expect(groupSummary(groups[1]!)).toBe("0 active, 1 needs attention");
    expect(groups[1]!.purposes).toEqual(["manager_approvals", "customer_messages"]);
  });

  it("says Switched off when nothing in the group works", () => {
    const [group] = groupConnections([connection("k1", "api", "disabled")]);
    expect(groupSummary(group!)).toBe("Switched off");
  });
});

describe("comingSoon", () => {
  const tool = (key: string): AvailableTool => ({
    provider_key: key,
    provider_name: key,
    kind: "one_click",
    purposes: [],
    free: true,
    cost_note: "",
  });

  it("lists WhatsApp, Email and SMS while none of them is installed", () => {
    expect(comingSoon(COMING_SOON, [tool("telegram")], []).map((item) => item.name)).toEqual([
      "WhatsApp",
      "Email",
      "SMS",
    ]);
  });

  it("drops a planned tool once its provider is installed or connected", () => {
    const left = comingSoon(COMING_SOON, [tool("whatsapp")], [connection("e1", "email", "active")]);
    expect(left.map((item) => item.provider_key)).toEqual(["sms"]);
  });
});
