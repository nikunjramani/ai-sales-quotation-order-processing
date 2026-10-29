import { useState } from "react";
import { Link, useParams } from "react-router";

import { LoginForm } from "@/features/account";
import { useSession, useSessionCache } from "@/features/auth";
import { ErrorMessage } from "@/shared/ui/QueryState";

import { useApprovalLink, useDecideByLink } from "../../hooks/useApprovalLink";
import type { ApprovalAction, ApprovalLink } from "../../model/types";
import {
  ACTION_LABEL,
  needsReason,
  recordedText,
  stateText,
} from "../../services/approvalLinkService";

/**
 * The signed approval link from a message (phase 5, P5-14). It needs sign-in as the manager
 * it was sent to; opening it changes nothing, a deliberate click decides on exactly the
 * version shown. Another person's link says so; an old one shows what happened instead.
 */
export function ApproveLinkPage() {
  const { token = "" } = useParams();
  const session = useSession();
  const cache = useSessionCache();
  const link = useApprovalLink(token, Boolean(session.data));
  return (
    <main className="narrow">
      <h1>Approval request</h1>
      {session.isLoading && <p className="muted">Loading…</p>}
      {!session.isLoading && !session.data && (
        <>
          <p>Sign in to see and decide this approval request.</p>
          <LoginForm onSignedIn={() => void cache.refresh()} />
        </>
      )}
      {link.isLoading && <p className="muted">Loading the request…</p>}
      <ErrorMessage message={link.error?.message} />
      {link.data && <Request link={link.data} token={token} />}
      <p>
        <Link to="/">Home</Link>
      </p>
    </main>
  );
}

function Request({ link, token }: { link: ApprovalLink; token: string }) {
  const decide = useDecideByLink(token);
  const [action, setAction] = useState<ApprovalAction | null>(null);
  const [reason, setReason] = useState("");
  const closed = stateText(link);
  const done = decide.data;
  const lines = link.content?.lines ?? [];
  const content = link.content;
  return (
    <section className="card">
      <h2>
        {link.business_name}: {link.number} version {link.version}
      </h2>
      {done && <p className="notice">{recordedText(done.action, link)}</p>}
      {!done && closed && <p className="notice">{closed}</p>}
      {link.state === "open" && content && (
        <>
          <p className="muted small">Customer reference: {link.customer_reference ?? "not given"}</p>
          <ul className="list">
            {lines.map((line) => (
              <li key={line.sku} className="row static">
                <span>
                  {line.sku} {line.description}: {line.quantity} {line.unit} × {line.unit_price} ={" "}
                  {line.line_total} {content.currency} (stock: {line.stock_status})
                </span>
              </li>
            ))}
          </ul>
          <p>
            Subtotal {content.subtotal} {content.currency}; tax {content.tax} {content.currency};{" "}
            <strong>
              total {content.total} {content.currency}
            </strong>
          </p>
          {(["approve", "reject", "request_revision"] as const).map((item) => (
            <button
              key={item}
              className={item === "approve" ? "primary" : item === "reject" ? "danger" : ""}
              disabled={decide.isPending}
              onClick={() => {
                if (needsReason(item)) {
                  setAction(item);
                  return;
                }
                decide.mutate({ action: item, contentSha256: link.content_sha256 ?? "" });
              }}
            >
              {ACTION_LABEL[item]}
            </button>
          ))}
          {action && needsReason(action) && (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                decide.mutate({
                  action,
                  contentSha256: link.content_sha256 ?? "",
                  reason: reason.trim(),
                });
              }}
            >
              <label>
                Reason
                <textarea
                  required
                  maxLength={1000}
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                />
              </label>
              <button className="primary" type="submit" disabled={!reason.trim()}>
                {ACTION_LABEL[action]}
              </button>
            </form>
          )}
        </>
      )}
      <ErrorMessage message={decide.error?.message} />
    </section>
  );
}
