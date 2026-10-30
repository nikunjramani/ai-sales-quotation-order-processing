import { useState, type FormEvent } from "react";

import { dateTime } from "@/shared/lib/format";
import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "../../hooks/useApiKeys";
import { ApiKeyCreatedDialog } from "../components/ApiKeyCreatedDialog";

/** Keys for the business's own website or system to send enquiries (Q17: intake keys only). */
export function ApiKeysPage() {
  const keys = useApiKeys();
  const create = useCreateApiKey();
  const revoke = useRevokeApiKey();
  const [name, setName] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    create.mutate(name, { onSuccess: () => setName("") });
  }

  return (
    <section>
      <h2>API keys</h2>
      {create.data ? (
        <ApiKeyCreatedDialog apiKey={create.data} onClose={() => create.reset()} />
      ) : (
        <form className="card" onSubmit={submit}>
          <label htmlFor="key-name">What is the key for?</label>
          <input
            id="key-name"
            required
            maxLength={100}
            placeholder="e.g. Website enquiry form"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <ErrorMessage message={create.error?.message} />
          <button type="submit" disabled={create.isPending}>
            Create key
          </button>
        </form>
      )}
      <QueryState
        isLoading={keys.isLoading}
        error={keys.error}
        isEmpty={keys.data?.length === 0}
        emptyText="No keys yet."
      >
        <ErrorMessage message={revoke.error?.message} />
        <ul className="list">
          {(keys.data ?? []).map((key) => (
            <li key={key.key_id} className="row static">
              <span>
                <strong>{key.name}</strong>{" "}
                <span className={`badge ${key.revoked_at ? "warn" : "good"}`}>
                  {key.revoked_at ? "Revoked" : "Active"}
                </span>
                <br />
                <span className="muted small">Created {dateTime(key.created_at)}</span>
              </span>
              {!key.revoked_at && (
                <button
                  className="danger"
                  disabled={revoke.isPending}
                  onClick={() => revoke.mutate(key.key_id)}
                >
                  Revoke
                </button>
              )}
            </li>
          ))}
        </ul>
      </QueryState>
    </section>
  );
}
