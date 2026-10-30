import { Clock } from "lucide-react";

import { QueryState } from "@/shared/ui/QueryState";

import { useAvailableTools, useConnections } from "../../hooks/useConnections";
import { COMING_SOON } from "../../services/comingSoon";
import { comingSoon, groupConnections } from "../../services/connectionService";
import { HostedChatCard } from "../components/HostedChatCard";
import { OneClickToolsCard } from "../components/OneClickToolsCard";
import { ToolGroupCard } from "../components/ToolGroupCard";

/**
 * Settings > Integrations (administrators): the business's connected tools grouped by kind,
 * the tools that can be added with one click, website chat, and the planned tools.
 * Every card comes from the installed providers, so a new tool needs no change here.
 */
export function IntegrationsPage() {
  const connections = useConnections(true);
  const available = useAvailableTools(true);
  const list = connections.data ?? [];
  const oneClick = new Set(
    (available.data ?? []).filter((tool) => tool.kind === "one_click").map((tool) => tool.provider_key),
  );
  const planned = comingSoon(COMING_SOON, available.data ?? [], list);
  return (
    <>
      <h2>Connected tools</h2>
      <QueryState
        isLoading={connections.isLoading}
        error={connections.error}
        isEmpty={list.length === 0}
        emptyText="No tools are connected yet. Add one below."
      >
        {groupConnections(list).map((group) => (
          <ToolGroupCard key={group.providerKey} group={group} oneClick={oneClick} />
        ))}
      </QueryState>

      <OneClickToolsCard connections={list} />
      <HostedChatCard connections={list} />

      {planned.length > 0 && (
        <section className="card">
          <h2>Coming soon</h2>
          <ul className="tool-grid">
            {planned.map((tool) => (
              <li key={tool.provider_key} className="tool-card soon" aria-disabled="true">
                <strong>{tool.name}</strong>
                <span className="muted small">{tool.description}</span>
                <span className="badge">
                  <Clock size={14} aria-hidden="true" /> Coming soon
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
