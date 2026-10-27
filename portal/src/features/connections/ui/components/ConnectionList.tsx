import { purposeText, STATUS_VIEW } from "../../services/connectionService";
import type { Connection } from "../../model/types";

/** The business's tools. Administrators also see technical errors (the API leaves them out for others). */
export function ConnectionList({ connections }: { connections: Connection[] }) {
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
              {connection.last_error && (
                <>
                  <br />
                  <span className="small">
                    Last error: {connection.last_error}
                  </span>
                </>
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
