import { useSession } from "@/features/auth";
import { ErrorMessage } from "@/shared/ui/QueryState";

import { useResendVerification } from "../../hooks/useEmailLinks";

/** Signed in but not verified yet (Q2): most things wait until the email link is opened. */
export function VerifyEmailBanner() {
  const session = useSession();
  const resend = useResendVerification();
  const user = session.data?.user;
  if (!user || user.email_verified) return null;
  return (
    <div className="card warn">
      <p>
        Confirm your email address <strong>{user.email}</strong> with the link we sent. Until then
        you cannot create a business or join one.
      </p>
      {resend.sent ? (
        <p className="muted small">A new email is on its way.</p>
      ) : (
        <button className="secondary" disabled={resend.busy} onClick={resend.resend}>
          Send the email again
        </button>
      )}
      <ErrorMessage message={resend.error} />
    </div>
  );
}
