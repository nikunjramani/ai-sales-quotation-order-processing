import { useCurrentTenant } from "@/features/tenant";
import { QueryState } from "@/shared/ui/QueryState";

import { useAvailableTools, useBindings, useConnections } from "../../hooks/useConnections";
import { BindingList } from "../components/BindingList";
import { ConnectionList } from "../components/ConnectionList";
import { HostedChatCard } from "../components/HostedChatCard";
import { LinkAccountCard } from "../components/LinkAccountCard";
import { OneClickToolsCard } from "../components/OneClickToolsCard";

/**
 * The business's tools and the accounts managers have linked. Administrators see every tool,
 * enable website chat and one-click tools (phase 5) and follow their setup step; approvers
 * see the tools they can link their own account to.
 */
export function ConnectionsPage() {
  const { can } = useCurrentTenant();
  const admin = can("integrations:manage");
  const approver = can("quotations:approve");
  const connections = useConnections(admin || approver);
  const bindings = useBindings();
  const available = useAvailableTools(admin);
  const oneClick = new Set(
    (available.data ?? [])
      .filter((tool) => tool.kind === "one_click")
      .map((tool) => tool.provider_key),
  );
  return (
    <section>
      <h1>Connections</h1>
      {(admin || approver) && (
        <QueryState
          isLoading={connections.isLoading}
          error={connections.error}
          isEmpty={connections.data?.length === 0}
          emptyText="No tools are connected."
        >
          <ConnectionList connections={connections.data ?? []} oneClick={oneClick} />
        </QueryState>
      )}
      {admin && <OneClickToolsCard connections={connections.data ?? []} />}
      {admin && <HostedChatCard connections={connections.data ?? []} />}
      <h2>Linked accounts</h2>
      {approver ? (
        <LinkAccountCard connections={connections.data ?? []} />
      ) : (
        <p className="muted">
          Only approvers can link an account for approvals.
        </p>
      )}
      <QueryState
        isLoading={bindings.isLoading}
        error={bindings.error}
        isEmpty={bindings.data?.length === 0}
        emptyText="No linked accounts."
      >
        <BindingList bindings={bindings.data ?? []} />
      </QueryState>
    </section>
  );
}
