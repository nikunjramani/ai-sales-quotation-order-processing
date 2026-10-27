import { Link } from "react-router";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useLinkToken, useVerifyEmail } from "../../hooks/useEmailLinks";

export function VerifyEmailPage() {
  const token = useLinkToken();
  const verify = useVerifyEmail(token);
  return (
    <main className="narrow">
      <h1>Confirm your email</h1>
      {verify.busy && <p className="muted">Checking the link…</p>}
      {verify.done && <p className="card">Your email address is confirmed.</p>}
      {!verify.busy && !verify.done && <ErrorMessage message={verify.error} />}
      <p>
        <Link to="/">Continue</Link>
      </p>
    </main>
  );
}
