import { Rocket } from "lucide-react";
import { Link } from "react-router";

import { useCurrentTenant } from "@/features/tenant";
import { PageHeader } from "@/shared/ui/PageHeader";
import { isApiError } from "@/shared/api/httpClient";
import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

import { useGoLive, useSetupChecklist } from "../../hooks/useBusiness";
import { missingFrom, remainingRequired, SETUP_STEPS } from "../../services/checklist";

/** The setup checklist (computed by the server from real data) and the Go live button. */
export function SetupPage() {
  const { can } = useCurrentTenant();
  const checklist = useSetupChecklist();
  const goLive = useGoLive();
  const data = checklist.data;
  const missing = isApiError(goLive.error, 409) ? missingFrom(goLive.error.detail) : [];
  return (
    <section>
      <PageHeader
        icon={Rocket}
        title="Get started"
        hint="Finish these steps one by one. When the required ones are done, press Go live."
      />
      <QueryState isLoading={checklist.isLoading} error={checklist.error}>
        {data && data.status === "active" && (
          <p className="card">Your business is live. Quotations can now reach customers.</p>
        )}
        <ul className="list">
          {data?.items.map((item) => {
            const step = SETUP_STEPS[item.key];
            return (
              <li key={item.key} className="row static">
                <span>
                  <span className={`badge ${item.done ? "good" : item.required ? "warn" : "info"}`}>
                    {item.done ? "Done" : item.required ? "To do" : "Later"}
                  </span>{" "}
                  <strong>{step.label}</strong>
                  <br />
                  <span className="muted small">{step.hint}</span>
                </span>
                {!item.done && step.link && <Link to={step.link}>Open</Link>}
              </li>
            );
          })}
        </ul>
        {data && data.status === "setting_up" && can("tenant:manage") && (
          <div className="card">
            {data.can_go_live ? (
              <p>Everything needed is done. Going live cannot be undone.</p>
            ) : (
              <p className="muted">{remainingRequired(data.items)} step(s) left before Go live.</p>
            )}
            <button
              className="primary"
              disabled={!data.can_go_live || goLive.isPending}
              onClick={() => goLive.mutate()}
            >
              Go live
            </button>
            {missing.length > 0 && (
              <p role="alert" className="error">
                Still missing: {missing.map((key) => SETUP_STEPS[key].label).join(", ")}
              </p>
            )}
            {!missing.length && <ErrorMessage message={goLive.error?.message} />}
          </div>
        )}
      </QueryState>
    </section>
  );
}
