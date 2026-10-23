import type { QuotationDetail } from "../../model/types";

export function QuotationHistory({ detail }: { detail: QuotationDetail }) {
  return (
    <section className="card">
      <h2>History</h2>
      <ol className="history">
        {detail.versions.map((version) => (
          <li key={`v${version.version}`}>
            Version {version.version} created by {version.created_by}
            {version.reason && <> — “{version.reason}”</>}
          </li>
        ))}
        {detail.decisions.map((decision) => (
          <li key={decision.decision_id}>
            Version {decision.version}: {decision.action.replace("_", " ")} by{" "}
            {decision.actor_subject} via {decision.transport}
            {decision.reason && <> — “{decision.reason}”</>}
          </li>
        ))}
      </ol>
    </section>
  );
}
