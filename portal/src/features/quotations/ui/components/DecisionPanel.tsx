import { ErrorMessage } from "@/shared/ui/QueryState";

import { useDecisionForm } from "../../hooks/useDecisionForm";
import type { Task } from "../../model/types";
import { DECISION_ACTIONS } from "../../services/quotationService";

/** Approve, reject or request a revision of the exact version on screen. */
export function DecisionPanel({ task }: { task: Task }) {
  const form = useDecisionForm(task);
  return (
    <section className="card" aria-label="Decision">
      <h2>Your decision on version {task.version}</h2>
      <label htmlFor="reason">Reason (required to reject or request a revision)</label>
      <textarea
        id="reason"
        rows={3}
        maxLength={1000}
        value={form.reason}
        onChange={(event) => form.setReason(event.target.value)}
      />
      <ErrorMessage message={form.error} />
      <div className="actions">
        {DECISION_ACTIONS.map((item) => (
          <button
            key={item.action}
            className={item.tone}
            disabled={form.busy}
            onClick={() => form.submit(item.action)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </section>
  );
}
