import { useSession } from "@/features/auth";
import { useCurrentTenant } from "@/features/tenant";
import { ErrorMessage } from "@/shared/ui/QueryState";

import { useLeaveBusiness } from "../../hooks/useMembers";

/** Anyone may leave the current business (Q22), except its last administrator. */
export function LeaveBusinessCard() {
  const session = useSession();
  const { tenant } = useCurrentTenant();
  const leave = useLeaveBusiness();
  const userId = session.data?.user?.user_id;
  if (!tenant || !userId) return null;
  return (
    <div className="card">
      <p>
        Leave <strong>{tenant.name}</strong>? You lose access at once; an administrator can
        invite you again.
      </p>
      <ErrorMessage
        message={
          leave.error?.message.includes("administrator")
            ? "You are the last administrator: make someone else administrator first."
            : leave.error?.message
        }
      />
      <button
        className="danger"
        disabled={leave.isPending}
        onClick={() => leave.mutate({ tenantId: tenant.tenant_id, userId })}
      >
        Leave this business
      </button>
    </div>
  );
}
