import { Link } from "react-router";

import { ErrorMessage } from "@/shared/ui/QueryState";

import { useForgotPasswordForm } from "../../hooks/useEmailLinks";
import { CHECK_EMAIL } from "../../services/links";

export function ForgotPasswordPage() {
  const form = useForgotPasswordForm();
  return (
    <main className="narrow">
      <h1>Forgot your password?</h1>
      {form.sent ? (
        <p className="card">{CHECK_EMAIL} The link works for 30 minutes.</p>
      ) : (
        <form className="card" onSubmit={form.submit}>
          <label htmlFor="forgot-email">Email</label>
          <input
            id="forgot-email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => form.setEmail(event.target.value)}
          />
          <ErrorMessage message={form.error} />
          <button type="submit" disabled={form.busy}>
            Send a reset link
          </button>
        </form>
      )}
      <p>
        <Link to="/login">Back to sign-in</Link>
      </p>
    </main>
  );
}
