import { useCurrentTenant } from "@/features/tenant";
import { QueryState } from "@/shared/ui/QueryState";

import { useBindings, useConnections } from "../../hooks/useConnections";
import { BindingList } from "../components/BindingList";
import { ConnectionList } from "../components/ConnectionList";
import { HostedChatCard } from "../components/HostedChatCard";
import { LinkAccountCard } from "../components/LinkAccountCard";

/**
 * The business's tools (website chat can be enabled here; other tools later) and the accounts
 * managers have linked. Administrators see every tool; approvers see the ones they can link.
 */
export function ConnectionsPage() {
  const { can } = useCurrentTenant();
  const admin = can("integrations:manage");
  const approver = can("quotations:approve");
  const connections = useConnections(admin || approver);
  const bindings = useBindings();
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
          <ConnectionList connections={connections.data ?? []} />
        </QueryState>
      )}
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
