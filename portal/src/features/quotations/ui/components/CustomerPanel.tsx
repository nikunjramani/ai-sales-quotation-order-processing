import { dateTime } from "@/shared/lib/format";
import { ErrorMessage, QueryState } from "@/shared/ui/QueryState";

import { useCustomerView, useWithdrawForm } from "../../hooks/useCustomerAnswer";
import type { CustomerView } from "../../model/types";
import { CUSTOMER_STATUS, OUTCOME_LABEL } from "../../services/customerService";

/** The customer's side: what they hold, until when, their answers, and withdrawal (M6). */
export function CustomerPanel({ quotationId }: { quotationId: string }) {
  const query = useCustomerView(quotationId);
  const view = query.data;
  if (view && view.customer_status === null && !view.responses.length) return null;
  return (
    <section className="card" aria-label="Customer">
      <h2>Customer</h2>
      <QueryState isLoading={query.isLoading} error={query.error}>
        {view && <CustomerDetails view={view} quotationId={quotationId} />}
      </QueryState>
    </section>
  );
}

function CustomerDetails({ view, quotationId }: { view: CustomerView; quotationId: string }) {
  const status = view.customer_status ? CUSTOMER_STATUS[view.customer_status] : null;
  return (
    <>
      {status && (
        <p>
          <span className={`badge ${status.tone}`}>{status.label}</span>{" "}
          <span className="muted small">
            Version {view.offered_version}
            {view.valid_until && <> · valid until {dateTime(view.valid_until)}</>}
          </span>
        </p>
      )}
      {view.responses.length > 0 && (
        <ol className="history">
          {view.responses.map((item) => (
            <li key={item.response_id}>
              Version {item.version}: {OUTCOME_LABEL[item.outcome]} ({dateTime(item.created_at)},{" "}
              {item.actor}){item.reason && <> — “{item.reason}”</>}
              {item.differences.length > 0 && (
                <ul className="small muted">
                  {item.differences.map((difference) => (
                    <li key={difference}>{difference}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ol>
      )}
      {view.can_withdraw && <WithdrawForm quotationId={quotationId} />}
    </>
  );
}

function WithdrawForm({ quotationId }: { quotationId: string }) {
  const form = useWithdrawForm(quotationId);
  return (
    <div>
      <label htmlFor="withdraw-reason">Withdraw this quotation (reason required)</label>
      <textarea
        id="withdraw-reason"
        rows={2}
        maxLength={1000}
        value={form.reason}
        onChange={(event) => form.setReason(event.target.value)}
      />
      <ErrorMessage message={form.error} />
      <div className="actions">
        <button className="danger" disabled={form.busy} onClick={form.submit}>
          Withdraw
        </button>
      </div>
    </div>
  );
}
