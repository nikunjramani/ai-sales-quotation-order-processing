import { Link } from "react-router";

import { useLinkToken, useResetPasswordForm } from "../../hooks/useEmailLinks";
import { PasswordField } from "../components/PasswordField";

export function ResetPasswordPage() {
  const token = useLinkToken();
  const form = useResetPasswordForm(token);
  return (
    <main className="narrow">
      <h1>Choose a new password</h1>
      {form.done ? (
        <p className="card">
          Your password is changed and every session was signed out.{" "}
          <Link to="/login">Sign in</Link>
        </p>
      ) : (
        <form className="card" onSubmit={form.submit}>
          <PasswordField
            label="New password"
            value={form.password}
            onChange={form.setPassword}
            autoComplete="new-password"
            hints={form.hints}
          />
          {form.errors.map((error) => (
            <p key={error} role="alert" className="error">
              {error}
            </p>
          ))}
          <button type="submit" disabled={form.busy || !token}>
            Save the new password
          </button>
        </form>
      )}
    </main>
  );
}
