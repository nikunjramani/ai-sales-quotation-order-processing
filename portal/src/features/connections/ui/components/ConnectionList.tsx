import { useState } from "react";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useOneClick } from "../../hooks/useConnections";
import type { Connection } from "../../model/types";
import { disableConfirmed, purposeText, STATUS_VIEW } from "../../services/connectionService";
import { PendingActionPanel } from "./PendingActionPanel";

/**
 * The business's tools. Administrators also see technical errors and what each tool reported
 * (the API leaves them out for others). One-click tools (phase 5) show the step left for the
 * business, and administrators can test or disable them.
 */
export function ConnectionList({
  connections,
  oneClick = new Set<string>(),
}: {
  connections: Connection[];
  /** Provider keys of one-click tools (from the available tools; admins only). */
  oneClick?: Set<string>;
}) {
  return (
    <ul className="list">
      {connections.map((connection) => {
        const status = STATUS_VIEW[connection.status];
        return (
          <li key={connection.connection_id} className="row static">
            <span>
              <strong>{connection.display_name}</strong>{" "}
              <span className={`badge ${status.tone}`}>{status.label}</span>
              <br />
              <span className="muted small">
                {connection.provider_name} · {purposeText(connection)}
              </span>
              {connection.detail && (
                <>
                  <br />
                  <span className="small">{connection.detail}</span>
                </>
              )}
              {connection.last_error && (
                <>
                  <br />
                  <span className="small">Last error: {connection.last_error}</span>
                </>
              )}
              <PendingActionPanel connection={connection} />
              {oneClick.has(connection.provider_key) && connection.status !== "disabled" && (
                <ToolActions connection={connection} />
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function ToolActions({ connection }: { connection: Connection }) {
  const actions = useOneClick();
  const [confirming, setConfirming] = useState(false);
  const [typed, setTyped] = useState("");
  const steps = actions.disable.data?.steps ?? [];
  const tested = actions.test.data;
  return (
    <div>
      <button
        disabled={actions.test.isPending}
        onClick={() => actions.test.mutate(connection.connection_id)}
      >
        Test
      </button>{" "}
      {!confirming && <button onClick={() => setConfirming(true)}>Disable…</button>}
      {tested && (
        <span className={`badge ${tested.ok ? "good" : "bad"}`}>
          {tested.ok ? "Working" : "Not working"}
          {tested.detail ? `: ${tested.detail}` : ""}
        </span>
      )}
      {confirming && (
        <div>
          <label>
            Customers and managers stop receiving messages from this tool. Type{" "}
            <strong>{connection.display_name}</strong> to confirm.
            <input value={typed} onChange={(event) => setTyped(event.target.value)} />
          </label>
          <button
            className="danger"
            disabled={!disableConfirmed(typed, connection) || actions.disable.isPending}
            onClick={() => actions.disable.mutate(connection.connection_id)}
          >
            Disable {connection.display_name}
          </button>{" "}
          <button onClick={() => setConfirming(false)}>Cancel</button>
        </div>
      )}
      {steps.length > 0 && (
        <div className="notice">
          Still to do in the tool itself:
          <ol>
            {steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      )}
      <ErrorMessage message={actions.test.error?.message ?? actions.disable.error?.message} />
    </div>
  );
}
