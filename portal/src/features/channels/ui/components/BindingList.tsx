import { ErrorMessage } from "@/shared/ui/QueryState";

import { useRevokeBinding } from "../../hooks/useChannels";
import type { Binding } from "../../model/types";

export function BindingList({ bindings }: { bindings: Binding[] }) {
  const revoke = useRevokeBinding();
  return (
    <>
      <ErrorMessage message={revoke.error?.message} />
      <ul className="list">
        {bindings.map((binding) => (
          <li key={binding.binding_id} className="row static">
            <span>
              <strong>{binding.external_user_id}</strong> on {binding.channel}
              <br />
              <span className="muted small">
                {binding.subject} · {binding.revoked_at ? "revoked" : "active"}
              </span>
            </span>
            {!binding.revoked_at && (
              <button
                className="danger"
                disabled={revoke.isPending}
                onClick={() => revoke.mutate(binding.binding_id)}
              >
                Revoke
              </button>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
