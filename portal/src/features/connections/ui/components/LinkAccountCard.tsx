import { ErrorMessage } from "@/shared/ui/QueryState";

import { useStartEnrollment } from "../../hooks/useConnections";
import type { Connection } from "../../model/types";
import { canLink } from "../../services/connectionService";

/**
 * Link your own account on a tool (e.g. a phone) so approval requests reach it and can be
 * answered there. Linking needs a one-time code sent from that account: proof that you control it.
 */
export function LinkAccountCard({
  connections,
}: {
  connections: Connection[];
}) {
  const enrollment = useStartEnrollment();
  const linkable = connections.filter(canLink);
  const code = enrollment.data?.code;
  const hint = enrollment.data?.hint;
  return (
    <div className="card">
      <p>
        Link your account so approval requests reach it and you can approve from
        there.
      </p>
      {linkable.length === 0 && (
        <p className="muted">No tool for approvals is connected yet.</p>
      )}
      {linkable.map((connection) => (
        <button
          key={connection.connection_id}
          className="primary"
          disabled={enrollment.isPending}
          onClick={() => enrollment.mutate(connection.connection_id)}
        >
          Link my account on {connection.display_name}
        </button>
      ))}
      <ErrorMessage message={enrollment.error?.message} />
      {code && !hint && (
        <p className="notice">
          Send this code from the account within 10 minutes: <code>{code}</code>
        </p>
      )}
      {code && hint && (
        <p className="notice">
          {hint.text}{" "}
          {hint.url ? (
            <a className="button primary" href={hint.url} target="_blank" rel="noreferrer">
              Open the link
            </a>
          ) : (
            <code>{code}</code>
          )}
        </p>
      )}
    </div>
  );
}
