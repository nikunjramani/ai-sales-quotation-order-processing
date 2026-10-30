import { ChevronDown, ChevronUp, Plug } from "lucide-react";
import { useState } from "react";

import { ToneBadge } from "@/shared/ui/StatusBadge";

import { groupSummary, PURPOSE_LABEL, type ToolGroup } from "../../services/connectionService";
import { ConnectionList } from "./ConnectionList";

/**
 * One connected kind of tool (for example all API keys) as a card. Working entries are listed;
 * switched-off ones stay hidden until "Show switched off" is pressed.
 */
export function ToolGroupCard({ group, oneClick }: { group: ToolGroup; oneClick: Set<string> }) {
  const [showOff, setShowOff] = useState(false);
  const tone = group.needsAttention ? "bad" : group.current.length ? "good" : "warn";
  return (
    <section className="card tool-group">
      <div className="tool-head">
        <span className="tool-icon" aria-hidden="true">
          <Plug size={24} />
        </span>
        <span className="tool-title">
          <strong>{group.providerName}</strong>
          <span className="muted small">
            {group.purposes.map((purpose) => PURPOSE_LABEL[purpose] ?? purpose).join(", ")}
          </span>
        </span>
        <ToneBadge tone={tone}>{groupSummary(group)}</ToneBadge>
      </div>
      {group.current.length > 0 && <ConnectionList connections={group.current} oneClick={oneClick} />}
      {group.switchedOff.length > 0 && (
        <>
          <button className="link" aria-expanded={showOff} onClick={() => setShowOff(!showOff)}>
            {showOff ? <ChevronUp size={18} aria-hidden="true" /> : <ChevronDown size={18} aria-hidden="true" />}
            {showOff ? "Hide switched off" : `Show switched off (${group.switchedOff.length})`}
          </button>
          {showOff && <ConnectionList connections={group.switchedOff} oneClick={oneClick} />}
        </>
      )}
    </section>
  );
}
