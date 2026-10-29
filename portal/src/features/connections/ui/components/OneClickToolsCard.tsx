import { useState } from "react";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useAvailableTools, useEnableDialog, useOneClick } from "../../hooks/useConnections";
import type { AvailableTool, Connection } from "../../model/types";
import { enablable, needsCostTick, PURPOSE_LABEL } from "../../services/connectionService";

/**
 * Tools we set up for the business with one click (phase 5). The cards come from the
 * installed providers, so a new tool appears here without a portal change. A tool that may
 * cost money asks the administrator to tick "I understand this may incur costs" first.
 */
export function OneClickToolsCard({ connections }: { connections: Connection[] }) {
  const available = useAvailableTools(true);
  const tools = enablable(available.data ?? [], connections);
  const { enabling, open } = useEnableDialog();
  if (tools.length === 0) return null;
  return (
    <section className="card">
      <h2>Add a tool</h2>
      <ul className="list">
        {tools.map((tool) => (
          <li key={tool.provider_key} className="row static">
            <span>
              <strong>{tool.provider_name}</strong>
              <br />
              <span className="muted small">
                {tool.purposes.map((purpose) => PURPOSE_LABEL[purpose] ?? purpose).join(", ")} ·{" "}
                {tool.cost_note}
              </span>
            </span>
            {enabling === tool.provider_key ? (
              <EnableDialog tool={tool} />
            ) : (
              <button onClick={() => open(tool.provider_key)}>Enable</button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function EnableDialog({ tool }: { tool: AvailableTool }) {
  const actions = useOneClick();
  const { close } = useEnableDialog();
  const [accepted, setAccepted] = useState(false);
  const costs = needsCostTick(tool);
  return (
    <div role="dialog" aria-label={`Enable ${tool.provider_name}`}>
      {costs && (
        <label>
          <input
            type="checkbox"
            checked={accepted}
            onChange={(event) => setAccepted(event.target.checked)}
          />{" "}
          I understand this may incur costs ({tool.cost_note})
        </label>
      )}
      <button
        className="primary"
        disabled={actions.enable.isPending || (costs && !accepted)}
        onClick={() =>
          actions.enable.mutate(
            { providerKey: tool.provider_key, acceptCosts: accepted },
            { onSuccess: close },
          )
        }
      >
        Enable {tool.provider_name}
      </button>
      <button onClick={close}>Cancel</button>
      <ErrorMessage message={actions.enable.error?.message} />
    </div>
  );
}
