import { Link } from "react-router";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useLinkToken } from "../../hooks/useEmailLinks";
import { useInvitation } from "../../hooks/useInvitation";
import { roleText } from "../../services/links";
import { LoginForm } from "../components/LoginForm";

/**
 * Opened from the invitation email. The link only works for the invited address: sign in (or
 * create the account in another tab first) with that address, then join.
 */
export function AcceptInvitationPage() {
  const token = useLinkToken();
  const invitation = useInvitation(token);
  const preview = invitation.preview;
  return (
    <main className="narrow">
      <h1>Join a business</h1>
      {invitation.loading && <p className="muted">Checking the invitation…</p>}
      {preview && (
        <div className="card">
          <p>
            You are invited to <strong>{preview.business_name}</strong> as{" "}
            {roleText(preview.roles)}, for <strong>{preview.email_hint}</strong>.
          </p>
          {invitation.signedIn ? (
            <button className="primary" disabled={invitation.busy} onClick={invitation.accept}>
              Join {preview.business_name}
            </button>
          ) : (
            <p className="muted small">
              Sign in with that address below. No account yet?{" "}
              <a href="#/signup" target="_blank" rel="noopener noreferrer">
                Create one in a new tab
              </a>
              , then come back here.
            </p>
          )}
        </div>
      )}
      <ErrorMessage message={invitation.loading ? null : invitation.error} />
      {preview && !invitation.signedIn && <LoginForm onSignedIn={() => undefined} />}
      <p>
        <Link to="/">Home</Link>
      </p>
    </main>
  );
}
