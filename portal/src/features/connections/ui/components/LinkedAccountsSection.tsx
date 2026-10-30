import { Smartphone } from "lucide-react";

import { QueryState } from "@/shared/ui/QueryState";

import { useBindings, useConnections } from "../../hooks/useConnections";
import { BindingList } from "./BindingList";
import { LinkAccountCard } from "./LinkAccountCard";

/**
 * "My linked accounts" on the profile page (managers): link your own phone or chat account so
 * approval requests reach you there, and see or remove the ones already linked.
 * Render it only inside a business (it reads the current business's tools).
 */
export function LinkedAccountsSection() {
  const connections = useConnections(true);
  const bindings = useBindings();
  return (
    <section>
      <h2>
        <Smartphone size={20} aria-hidden="true" /> My linked accounts
      </h2>
      <p className="hint">Link your phone or chat app so approval requests reach you there.</p>
      <LinkAccountCard connections={connections.data ?? []} />
      <QueryState
        isLoading={bindings.isLoading}
        error={bindings.error}
        isEmpty={bindings.data?.length === 0}
        emptyText="No linked accounts yet."
      >
        <BindingList bindings={bindings.data ?? []} />
      </QueryState>
    </section>
  );
}
