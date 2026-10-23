import type { PricingIssue } from "../../model/types";

export function PricingIssuesCard({ issues }: { issues: PricingIssue[] }) {
  if (!issues.length) return null;
  return (
    <section className="card warn">
      <h2>Could not be priced</h2>
      <ul>
        {issues.map((issue) => (
          <li key={`${issue.line_index}-${issue.code}`}>
            {issue.sku}: {issue.message}
          </li>
        ))}
      </ul>
    </section>
  );
}
