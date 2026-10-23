import { useCurrentTenant } from "@/features/tenant";
import { QueryState } from "@/shared/ui/QueryState";

import { useBindings } from "../../hooks/useChannels";
import { BindingList } from "../components/BindingList";
import { EnrollmentCard } from "../components/EnrollmentCard";

export function ChannelsPage() {
  const { can } = useCurrentTenant();
  const bindings = useBindings();
  return (
    <section>
      <h1>Approval channels</h1>
      {can("quotations:approve") ? (
        <EnrollmentCard />
      ) : (
        <p className="muted">Only approvers can link approval channels.</p>
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
